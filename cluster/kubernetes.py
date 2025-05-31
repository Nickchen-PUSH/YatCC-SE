"""Kubernetes 集群实现

专门针对用户独立的 code-server 镜像的部署和管理。
"""

import asyncio as aio
import threading
import socket
import subprocess
from base.logger import logger
from datetime import datetime
from typing import Any, List, Optional, Dict
from kubernetes.client.rest import ApiException
from dataclasses import dataclass

from config import CONFIG, Config
from . import (
    ClusterABC,
    JobParams,
    JobInfo,
    ClusterError,
    JobNotFoundError,
)

LOGGER = logger(__spec__, __file__)


@dataclass
class KubernetesSpec:
    """Kubernetes 规格配置"""

    def __init__(self, job_params: JobParams):
        self.job_params = job_params

    def _build_deployment(self) -> Dict[str, Any]:
        """构建完整的 Deployment 规格"""
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": self.job_params.name,
                "labels": self._build_labels(),
                "namespace": CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            },
            "spec": self._build_spec(),
        }

    def _build_service(self) -> Dict[str, Any]:
        """构建 Service 规格"""
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": self.job_params.name + "-svc",
                "labels": self._build_labels(),
                "namespace": CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            },
            "spec": {
                "selector": {"app": self.job_params.name, **self._build_labels()},
                "ports": [
                    {
                        "port": CONFIG.CLUSTER.Codespace.PORT,
                        "targetPort": CONFIG.CLUSTER.Codespace.PORT,
                        "protocol": "TCP",
                        "name": "http",
                    }
                ],
                "type": "NodePort",
            },
        }

    def _build_spec(self) -> Dict[str, Any]:
        return {
            "replicas": 1,
            "selector": {"matchLabels": {"app": self.job_params.name}},
            "template": {
                "metadata": {
                    "labels": {"app": self.job_params.name, **self._build_labels()}
                },
                "spec": self._build_pod_spec(),
            },
        }

    def _build_pod_spec(self) -> Dict[str, Any]:
        return {
            "containers": [self._build_container()],
            "volumes": self._build_volumes(),
            "restartPolicy": "Always",
        }

    def _build_container(self) -> Dict[str, Any]:
        return {
            "name": "code-server",
            "image": self.job_params.image,
            "ports": [{"containerPort": CONFIG.CLUSTER.Codespace.PORT}],
            "env": [{"name": k, "value": v} for k, v in self.job_params.env.items()],
            "args": [
                "--bind-addr=0.0.0.0:8080",
                "--auth=password",
                "--disable-telemetry",
                "/workspace",
            ],
            "volumeMounts": self._build_volume_mounts(),
            "resources": self._build_resources(),
            "readinessProbe": self._build_probe(),
            "livenessProbe": self._build_probe(initial_delay=60, period=30),
        }

    def _build_volume_mounts(self) -> List[Dict[str, str]]:
        return [
            {"name": "code", "mountPath": "/workspace"},
            {"name": "io", "mountPath": "/io"},
            {"name": "root", "mountPath": "/data"},
        ]

    def _build_volumes(self) -> List[Dict[str, Any]]:
        base_path = f"{CONFIG.CORE.students_dir}/{self.job_params.user_id}"
        return [
            {
                "name": name,
                "hostPath": {
                    "path": f"{base_path}/{name}",
                    "type": "DirectoryOrCreate",
                },
            }
            for name in ["code", "io", "root"]
        ]

    def _build_resources(self) -> Dict[str, Dict[str, str]]:
        return {
            "requests": {"memory": "256Mi", "cpu": "250m"},
            "limits": {
                "memory": self.job_params.memory_limit
                or CONFIG.CLUSTER.Codespace.DEFAULT_MEMORY_LIMIT,
                "cpu": self.job_params.cpu_limit
                or CONFIG.CLUSTER.Codespace.DEFAULT_CPU_LIMIT,
            },
        }

    def _build_probe(self, initial_delay: int = 30, period: int = 10) -> Dict[str, Any]:
        return {
            "httpGet": {"path": "/", "port": CONFIG.CLUSTER.Codespace.PORT},
            "initialDelaySeconds": initial_delay,
            "periodSeconds": period,
        }

    def _build_labels(self) -> Dict[str, str]:
        return {
            "managed-by": "yatcc-se",
            "user-id": self.job_params.user_id,
            "type": "code-server",
        }


class KubernetesCluster(ClusterABC):
    """Kubernetes 集群实现"""

    def __init__(self):
        self._k8s_client = None
        self._apps_v1 = None
        self._core_v1 = None
        self._is_initialized = False
        self._port_forwards: Dict[str, Dict] = {}
        self._local_port_base = 30000  # 本地端口基数，用于端口转发

    async def initialize(self):
        """初始化 Kubernetes 集群连接"""
        if self._is_initialized:
            return

        try:
            # 导入 Kubernetes 客户端
            from kubernetes import client, config as k8s_config

            # 尝试加载配置
            try:
                k8s_config.load_kube_config()
                LOGGER.info("Loaded kubeconfig from file")
            except Exception:
                try:
                    # 如果在集群内，尝试加载集群内配置
                    k8s_config.load_incluster_config()
                    LOGGER.info("Loaded in-cluster config")
                except Exception as e:
                    raise ClusterError(f"Failed to load Kubernetes config: {e}")

            # 创建客户端
            self._k8s_client = client.ApiClient()
            self._apps_v1 = client.AppsV1Api()
            self._core_v1 = client.CoreV1Api()

            # 测试连接
            await aio.to_thread(self._core_v1.list_namespace, timeout_seconds=10)

            self._is_initialized = True
            LOGGER.info("Kubernetes cluster initialized successfully")

        except Exception as e:
            LOGGER.error(f"Failed to initialize Kubernetes cluster: {e}")
            raise ClusterError(f"Kubernetes initialization failed: {e}")

    async def ensure_initialized(self):
        """确保已初始化"""
        if not self._is_initialized:
            await self.initialize()

    @property
    def apps_v1(self):
        """获取 AppsV1Api 客户端"""
        return self._apps_v1

    @property
    def core_v1(self):
        """获取 CoreV1Api 客户端"""
        return self._core_v1

    async def allocate_resources(self, job_params):
        """创建作业"""
        await self.ensure_initialized()
        try:
            # 创建 Deployment
            deployment_spec = KubernetesSpec(job_params)._build_deployment()

            await aio.to_thread(
                self.apps_v1.create_namespaced_deployment,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                body=deployment_spec,
            )
            LOGGER.info(f"Created Deployment: {job_params.name}")

            # 创建 Service
            await self._create_service(job_params)
            LOGGER.info(f"Created Service for Deployment: {job_params.name}")

            service_url = await self.get_service_url(job_params.name)

            return JobInfo(
                id=job_params.name,
                name=job_params.name,
                image=job_params.image,
                ports=job_params.ports,
                env=job_params.env,
                status=JobInfo.Status.RUNNING,
                created_at=datetime.now().isoformat(),
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                service_url=service_url,
                user_id=job_params.user_id,
            )

        except Exception as e:
            LOGGER.error(f"Failed to submit job: {e}")
            # 清理可能创建的资源
            await self._cleanup_job_resources(job_params.name)
            raise ClusterError(f"Failed to submit job: {e}")

    async def submit_job(self, job_params: JobParams) -> JobInfo:
        """提交 code-server 作业到 Kubernetes"""
        await self.ensure_initialized()

        # 验证必需参数
        if not job_params.user_id:
            raise ValueError("job_user_id is required")

        existing_job = None
        deployments = await aio.to_thread(
            self.apps_v1.list_namespaced_deployment,
            namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            label_selector=f"managed-by=yatcc-se,user-id={job_params.user_id},type=code-server",
        )

        if deployments.items:
            deployment = deployments.items[0]
            job_name = deployment.metadata.name
            LOGGER.info(
                f"Found existing deployment for user {job_params.user_id}: {job_name}"
            )
            existing_job = job_name

        if existing_job:
            return await self._resume_user_deployment(existing_job, job_params)
        else:
            LOGGER.info(
                "No existing deployment found for user {job_params.user_id}, creating a new one."
            )
            return await self.allocate_resources(job_params)

    async def _resume_user_deployment(
        self, job_name: str, job_params: JobParams
    ) -> JobInfo:
        """恢复用户的 Deployment"""
        try:
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            # 检查是否被暂停
            annotations = deployment.metadata.annotations or {}
            is_suspended = annotations.get("yatcc-se/suspended") == "true"

            LOGGER.info(f"Checking deployment {job_name} suspension status:")
            LOGGER.info(f"  - Annotations: {annotations}")
            LOGGER.info(f"  - Is suspended: {is_suspended}")

            if is_suspended:
                # 恢复 Deployment
                LOGGER.info(f"Unsuspending deployment: {job_name}")
                await self._unsuspend_deployment(job_name)
                LOGGER.info(f"Resumed suspended deployment: {job_name}")

                # 等待一下，然后重新读取 deployment 以获取最新状态
                await aio.sleep(2)
                deployment = await aio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=job_name,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                )

                # 验证注解是否被移除
                updated_annotations = deployment.metadata.annotations or {}
                LOGGER.info(f"After unsuspend, annotations: {updated_annotations}")
            else:
                # Deployment 已经在运行
                LOGGER.info(f"Deployment {job_name} is already running")

            # 🎯 更新环境变量和配置
            await self._update_deploy_spec(job_params)

            # 确保 Service 存在
            service_url = await self._check_service(job_params)

            # 再次读取最新的 deployment 状态
            final_deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            # 返回 JobInfo
            container = final_deployment.spec.template.spec.containers[0]
            labels = final_deployment.metadata.labels or {}

            # 确定状态
            if (
                final_deployment.status.ready_replicas
                and final_deployment.status.ready_replicas >= 1
            ):
                status = JobInfo.Status.RUNNING
            elif final_deployment.status.unavailable_replicas:
                status = JobInfo.Status.FAILED
            else:
                status = JobInfo.Status.PENDING
            user_id = labels.get("user-id", 0)
            if user_id is not None:
                user_id = str(user_id)
            return JobInfo(
                id=final_deployment.metadata.name,
                name=final_deployment.metadata.name,
                image=container.image,
                ports=[CONFIG.CLUSTER.Codespace.PORT],
                env={env_var.name: env_var.value for env_var in (container.env or [])},
                status=status,
                created_at=(
                    final_deployment.metadata.creation_timestamp.isoformat()
                    if final_deployment.metadata.creation_timestamp
                    else None
                ),
                namespace=final_deployment.metadata.namespace,
                service_url=service_url,
                user_id=user_id,
            )

        except ApiException as e:
            raise ClusterError(f"Failed to resume deployment: {e}")

    async def _unsuspend_deployment(self, job_name: str) -> None:
        """恢复被暂停的 Deployment"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                LOGGER.info(
                    f"Unsuspending deployment {job_name} (attempt {attempt + 1})"
                )

                # 重新读取最新的 deployment
                deployment = await aio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=job_name,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                )

                annotations = deployment.metadata.annotations or {}
                LOGGER.info(f"Current annotations before unsuspend: {annotations}")

                # 修复：正确获取原始副本数
                original_replicas_str = annotations.get(
                    "yatcc-se/original-replicas", "1"
                )
                try:
                    original_replicas = int(original_replicas_str)
                except ValueError:
                    LOGGER.warning(
                        f"Invalid original-replicas value: {original_replicas_str}, using default 1"
                    )
                    original_replicas = 1

                # 恢复副本数
                deployment.spec.replicas = original_replicas
                LOGGER.info(f"Setting replicas to: {original_replicas}")

                # 🎯 关键修复：确保注解被完全删除
                # 创建新的注解字典，排除暂停相关的注解
                new_annotations = {}
                for key, value in annotations.items():
                    if key not in ["yatcc-se/suspended", "yatcc-se/original-replicas"]:
                        new_annotations[key] = value

                # 设置新的注解字典
                deployment.metadata.annotations = new_annotations

                LOGGER.info(f"New annotations after removal: {new_annotations}")
                LOGGER.info(
                    f"Removed annotations: yatcc-se/suspended, yatcc-se/original-replicas"
                )

                # 执行更新
                updated_deployment = await aio.to_thread(
                    self.apps_v1.patch_namespaced_deployment,
                    name=job_name,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                    body=deployment,
                )

                LOGGER.info(f"Successfully unsuspended deployment: {job_name}")
                LOGGER.info(f"Final replicas: {updated_deployment.spec.replicas}")
                LOGGER.info(
                    f"Final annotations: {updated_deployment.metadata.annotations}"
                )
                return

            except ApiException as e:
                if e.status == 409 and attempt < max_retries - 1:
                    # 版本冲突，等待一下再重试
                    LOGGER.warning(
                        f"Deployment {job_name} version conflict, retrying... (attempt {attempt + 1})"
                    )
                    await aio.sleep(0.5 * (attempt + 1))  # 递增等待时间
                    continue
                elif e.status == 404:
                    LOGGER.warning(f"Deployment {job_name} not found during unsuspend")
                    return
                else:
                    raise ClusterError(f"Failed to unsuspend deployment: {e}")
            except Exception as e:
                LOGGER.error(f"Unexpected error unsuspending {job_name}: {e}")
                raise ClusterError(f"Unexpected error unsuspending deployment: {e}")

    async def _update_deploy_spec(self, job_params: JobParams) -> bool:
        """更新 Deployment 的配置"""
        job_name = job_params.name
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 重新读取最新的 deployment
                deployment = await aio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=job_name,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                )

                container = deployment.spec.template.spec.containers[0]
                # 更新环境变量
                container.env = [
                    {"name": k, "value": v} for k, v in job_params.env.items()
                ]

                # 更新资源限制
                container.resources.limits = {
                    "memory": job_params.memory_limit
                    or CONFIG.CLUSTER.Codespace.DEFAULT_MEMORY_LIMIT,
                    "cpu": job_params.cpu_limit
                    or CONFIG.CLUSTER.Codespace.DEFAULT_CPU_LIMIT,
                }

                await aio.to_thread(
                    self.apps_v1.patch_namespaced_deployment,
                    name=job_name,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                    body=deployment,
                )

                LOGGER.info(f"Updated deployment configuration: {job_name}")
                return True
            except ApiException as e:
                if e.status == 409 and attempt < max_retries - 1:
                    # 版本冲突，等待一下再重试
                    LOGGER.warning(
                        f"Deployment {job_name} update conflict, retrying... (attempt {attempt + 1})"
                    )
                    await aio.sleep(0.5 * (attempt + 1))
                    continue
                elif e.status == 404:
                    LOGGER.warning(f"Deployment {job_name} not found during update")
                    return False
                else:
                    LOGGER.warning(f"Failed to update deployment {job_name}: {e}")
                    return False

        LOGGER.warning(
            f"Failed to update deployment {job_name} after {max_retries} attempts"
        )
        return False

    async def _check_service(self, job_params: JobParams) -> str:
        """确保 Service 存在"""
        svc_name = job_params.name + "-svc"

        try:
            service = await aio.to_thread(
                self.core_v1.read_namespaced_service,
                name=svc_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            # Service 存在，返回 URL
            return f"http://{service.metadata.name}.{service.metadata.namespace}.svc.cluster.local:{service.spec.ports[0].port}"

        except ApiException as e:
            if e.status == 404:
                # Service 不存在，创建它
                LOGGER.info(f"Service not found for {svc_name}, creating...")
                return await self._create_service(job_params)
            raise ClusterError(f"Failed to check service: {e}")

    async def _create_service(self, job_params: JobParams) -> str:
        """创建 Service，返回内部集群 URL"""
        service_spec = KubernetesSpec(job_params)._build_service()
        svc_name = service_spec["metadata"]["name"]
        service = await aio.to_thread(
            self.core_v1.create_namespaced_service,
            namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            body=service_spec,
        )

        node_port = service.spec.ports[0].node_port
        service.nodeport = node_port

        # 返回内部集群 URL
        service_url = f"http://{svc_name}.{CONFIG.CLUSTER.Kubernetes.NAMESPACE}.svc.cluster.local:{CONFIG.CLUSTER.Codespace.PORT}"
        LOGGER.info(f"Created Service: {svc_name}, Internal URL: {service_url}")
        return service_url

    async def get_service_url(self, job_name: str) -> str:
        """获取指定作业的服务访问 URL - 创建端口转发并返回本地 URL"""
        await self.ensure_initialized()
        try:
            # 先检查 Service 是否存在
            service = await aio.to_thread(
                self.core_v1.read_namespaced_service,
                name=f"{job_name}-svc",
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            # 检查是否已有端口转发
            if job_name in self._port_forwards:
                forward_info = self._port_forwards[job_name]
                if forward_info["thread"].is_alive():
                    local_url = f"http://localhost:{forward_info['local_port']}"
                    LOGGER.debug(
                        f"Using existing port forward for {job_name}: {local_url}"
                    )
                    return local_url
                else:
                    # 清理无效的端口转发
                    del self._port_forwards[job_name]

            # 创建新的端口转发
            local_port = self._get_available_local_port()
            target_port = service.spec.ports[0].port

            # 使用 kubectl port-forward 创建端口转发
            success = await self._create_kubectl_port_forward(
                job_name=job_name, local_port=local_port, target_port=target_port
            )

            if success:
                local_url = f"http://localhost:{local_port}"
                LOGGER.info(
                    f"Created port forward for {job_name}: {local_url} -> {target_port}"
                )
                return local_url
            else:
                raise ClusterError(f"Failed to create port forward for {job_name}")

        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Service not found for job: {job_name}")
            raise ClusterError(f"Failed to get service URL: {e}")

    async def _create_kubectl_port_forward(
        self, job_name: str, local_port: int, target_port: int
    ) -> bool:
        """使用 kubectl port-forward 创建端口转发"""
        import subprocess

        def port_forward_worker():
            process = None
            try:
                service_name = f"{job_name}-svc"

                # 构建 kubectl port-forward 命令
                cmd = [
                    "kubectl",
                    "port-forward",
                    f"svc/{service_name}",
                    f"{local_port}:{target_port}",
                    "-n",
                    CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                ]

                LOGGER.info(f"Starting port forward: {' '.join(cmd)}")

                # 启动端口转发进程
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )

                # 保存进程引用
                forward_info = self._port_forwards.get(job_name, {})
                forward_info["process"] = process
                self._port_forwards[job_name] = forward_info

                # 等待进程结束或停止信号
                stop_event = forward_info.get("stop_event", threading.Event())

                # 读取一些初始输出来检查是否成功启动
                import select
                import time

                initial_output_read = False

                while not stop_event.is_set():
                    if process.poll() is not None:
                        # 进程已结束，读取所有输出并关闭文件句柄
                        try:
                            stdout, stderr = process.communicate(timeout=5)
                            if stderr:
                                LOGGER.error(
                                    f"Port forward error for {job_name}: {stderr}"
                                )
                                if "pod is not running" in stderr:
                                    LOGGER.warning(
                                        f"Pod for {job_name} is not running yet"
                                    )
                                elif "unable to forward port" in stderr:
                                    LOGGER.warning(
                                        f"Unable to forward port for {job_name}"
                                    )
                        except subprocess.TimeoutExpired:
                            # 强制终止并读取输出
                            process.kill()
                            stdout, stderr = process.communicate()
                            LOGGER.warning(
                                f"Port forward process killed for {job_name}"
                            )
                        break

                    # 如果是第一次循环，尝试读取一些初始输出
                    if not initial_output_read:
                        time.sleep(2)  # 给进程一些启动时间
                        initial_output_read = True

                    time.sleep(1)

            except Exception as e:
                LOGGER.error(f"Port forward worker error for {job_name}: {e}")
            finally:
                # 确保进程被正确清理
                if process is not None:
                    try:
                        if process.poll() is None:
                            # 进程仍在运行，终止它
                            process.terminate()
                            try:
                                # 等待进程结束并读取输出以关闭文件句柄
                                stdout, stderr = process.communicate(timeout=5)
                            except subprocess.TimeoutExpired:
                                # 如果等待超时，强制杀死进程
                                process.kill()
                                stdout, stderr = process.communicate()
                    except Exception as cleanup_error:
                        LOGGER.warning(
                            f"Error during process cleanup for {job_name}: {cleanup_error}"
                        )

        try:
            # 在启动端口转发之前，先检查 Pod 状态
            try:
                pods = await aio.to_thread(
                    self.core_v1.list_namespaced_pod,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                    label_selector=f"app={job_name}",
                )

                if not pods.items:
                    LOGGER.warning(f"No pods found for job {job_name}")
                    return False

                pod = pods.items[0]
                if pod.status.phase != "Running":
                    LOGGER.warning(
                        f"Pod {pod.metadata.name} is not running (phase: {pod.status.phase})"
                    )
                    # 仍然尝试创建端口转发，但预期会失败
                else:
                    # 检查容器是否就绪
                    if pod.status.container_statuses:
                        ready_containers = [
                            cs for cs in pod.status.container_statuses if cs.ready
                        ]
                        if not ready_containers:
                            LOGGER.warning(
                                f"Pod {pod.metadata.name} is running but no containers are ready"
                            )

            except Exception as e:
                LOGGER.warning(f"Failed to check pod status before port forward: {e}")

            # 创建停止事件
            stop_event = threading.Event()

            # 启动端口转发线程
            thread = threading.Thread(target=port_forward_worker, daemon=True)
            thread.start()

            # 存储端口转发信息
            self._port_forwards[job_name] = {
                "thread": thread,
                "local_port": local_port,
                "target_port": target_port,
                "service_name": f"{job_name}-svc",
                "stop_event": stop_event,
                "process": None,  # 将在线程中设置
            }

            # 等待端口转发建立，但时间更短
            for i in range(5):  # 最多等待 5 秒
                await aio.sleep(1)
                if await self._test_local_port(local_port):
                    LOGGER.info(
                        f"Port forward established for {job_name} on localhost:{local_port}"
                    )
                    return True

            # 如果 5 秒后仍不可用，记录警告但不清理（可能 Pod 还在启动）
            LOGGER.warning(f"Port forward not ready yet for {job_name} after 5s")
            return True  # 返回 True，让调用者知道端口转发已启动，即使还不可用

        except Exception as e:
            LOGGER.error(f"Failed to create port forward for {job_name}: {e}")
            return False

    async def _test_local_port(self, port: int) -> bool:
        """测试本地端口是否可用"""
        try:
            future = aio.get_event_loop().run_in_executor(
                None, self._sync_test_local_port, port
            )
            return await future
        except Exception:
            return False

    def _sync_test_local_port(self, port: int) -> bool:
        """同步测试本地端口"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex(("localhost", port))
                return result == 0
        except Exception:
            return False

    async def stop_port_forward(self, job_name: str) -> None:
        """停止指定作业的端口转发"""
        if job_name in self._port_forwards:
            forward_info = self._port_forwards[job_name]

            # 设置停止事件
            if "stop_event" in forward_info:
                forward_info["stop_event"].set()

            # 终止进程并确保文件句柄被关闭
            if "process" in forward_info and forward_info["process"]:
                process = forward_info["process"]
                try:
                    if process.poll() is None:
                        # 进程仍在运行，终止它
                        process.terminate()
                        try:
                            # 等待进程结束并读取输出以关闭文件句柄
                            stdout, stderr = process.communicate(timeout=5)
                            LOGGER.debug(
                                f"Port forward process terminated gracefully for {job_name}"
                            )
                        except subprocess.TimeoutExpired:
                            # 如果等待超时，强制杀死进程
                            process.kill()
                            stdout, stderr = process.communicate()
                            LOGGER.warning(
                                f"Port forward process killed for {job_name}"
                            )
                    else:
                        # 进程已经结束，但仍需要读取输出以关闭文件句柄
                        try:
                            stdout, stderr = process.communicate(timeout=1)
                        except subprocess.TimeoutExpired:
                            # 这种情况不太可能发生，但以防万一
                            LOGGER.warning(
                                f"Failed to read output from terminated process for {job_name}"
                            )
                except Exception as e:
                    LOGGER.warning(
                        f"Error stopping port forward process for {job_name}: {e}"
                    )

            # 等待线程结束
            if "thread" in forward_info and forward_info["thread"].is_alive():
                forward_info["thread"].join(timeout=5)
                if forward_info["thread"].is_alive():
                    LOGGER.warning(
                        f"Port forward thread did not stop within timeout for {job_name}"
                    )

            del self._port_forwards[job_name]
            LOGGER.info(f"Stopped port forward for {job_name}")

    def _get_available_local_port(self) -> int:
        """获取可用的本地端口"""
        for port in range(self._local_port_base, self._local_port_base + 1000):
            if port not in [
                info["local_port"] for info in self._port_forwards.values()
            ]:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    try:
                        sock.bind(("localhost", port))
                        return port
                    except OSError:
                        continue
        raise ClusterError("No available local port found")

    async def get_job_status(self, job_name: str) -> JobInfo.Status:
        """获取作业状态"""
        await self.ensure_initialized()
        try:
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            # 确定状态
            if (
                deployment.status.ready_replicas
                and deployment.status.ready_replicas >= 1
            ):
                return JobInfo.Status.RUNNING
            elif deployment.status.unavailable_replicas:
                return JobInfo.Status.FAILED
            else:
                return JobInfo.Status.PENDING
        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_name}")
            raise ClusterError(f"Failed to get job status: {e}")

    async def get_job_info(self, job_name: str) -> JobInfo:
        """获取作业详细信息"""
        await self.ensure_initialized()
        try:
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            container = deployment.spec.template.spec.containers[0]
            labels = deployment.metadata.labels or {}

            # 确定状态
            if (
                deployment.status.ready_replicas
                and deployment.status.ready_replicas >= 1
            ):
                status = JobInfo.Status.RUNNING
            elif deployment.status.unavailable_replicas:
                status = JobInfo.Status.FAILED
            else:
                status = JobInfo.Status.PENDING

            # 获取服务 URL
            service_url = None
            try:
                service = await aio.to_thread(
                    self.core_v1.read_namespaced_service,
                    name=f"{job_name}-svc",
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                )
                service_url = f"http://{service.metadata.name}.{service.metadata.namespace}.svc.cluster.local:{CONFIG.CLUSTER.Codespace.PORT}"
            except ApiException:
                pass

            user_id = labels.get("user-id")
            if user_id is not None:
                user_id = str(user_id)

            return JobInfo(
                id=deployment.metadata.name,
                name=deployment.metadata.name,
                image=container.image,
                ports=[CONFIG.CLUSTER.Codespace.PORT],
                env={env_var.name: env_var.value for env_var in (container.env or [])},
                status=status,
                created_at=(
                    deployment.metadata.creation_timestamp.isoformat()
                    if deployment.metadata.creation_timestamp
                    else None
                ),
                namespace=deployment.metadata.namespace,
                service_url=service_url,
                user_id=user_id,
            )

        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_name}")
            raise ClusterError(f"Failed to get job info: {e}")

    async def delete_job(self, job_name: str) -> List[str]:
        """根据作业名称暂停指定的 Deployment"""
        await self.ensure_initialized()
        try:
            # 直接尝试读取指定名称的 deployment
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            deployment_name = deployment.metadata.name
            current_replicas = deployment.spec.replicas or 1

            # 停止端口转发
            await self.stop_port_forward(deployment_name)

            # 使用重试机制更新 deployment
            success = await self._suspend_deployment(deployment_name, current_replicas)
            if success:
                LOGGER.info(f"Suspended deployment: {deployment_name}")
                return [deployment_name]
            else:
                LOGGER.warning(f"Failed to suspend deployment: {deployment_name}")
                raise ClusterError(f"Failed to suspend deployment: {deployment_name}")

        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_name}")
            raise ClusterError(f"Failed to suspend deployment: {e}")

    async def _suspend_deployment(self, job_name: str, original_replicas: int) -> bool:
        """使用重试机制暂停 deployment"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 重新读取最新的 deployment
                deployment = await aio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=job_name,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                )

                # 保存当前副本数到注解中，以便恢复
                annotations = deployment.metadata.annotations or {}
                annotations["yatcc-se/suspended"] = "true"
                annotations["yatcc-se/original-replicas"] = str(original_replicas)

                # 更新 Deployment：设置副本数为 0 并添加注解
                deployment.spec.replicas = 0
                deployment.metadata.annotations = annotations

                await aio.to_thread(
                    self.apps_v1.patch_namespaced_deployment,
                    name=job_name,
                    namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                    body=deployment,
                )

                return True

            except ApiException as e:
                if e.status == 409 and attempt < max_retries - 1:
                    # 版本冲突，等待一下再重试
                    LOGGER.warning(
                        f"Deployment {job_name} suspend conflict, retrying... (attempt {attempt + 1})"
                    )
                    await aio.sleep(0.5 * (attempt + 1))
                    continue
                elif e.status == 404:
                    LOGGER.warning(f"Deployment {job_name} not found during suspend")
                    return False
                else:
                    LOGGER.error(f"Failed to suspend deployment {job_name}: {e}")
                    return False

        LOGGER.error(
            f"Failed to suspend deployment {job_name} after {max_retries} attempts"
        )
        return False

    async def cleanup_resources(self, job_name: str) -> None:
        """释放作业"""
        await self.ensure_initialized()
        try:
            await self.stop_port_forward(job_name)

            await self._cleanup_job_resources(job_name)
            LOGGER.info(f"Job deleted: {job_name}")
        except ApiException as e:
            if e.status != 404:
                raise ClusterError(f"Failed to delete job: {e}")

    async def _cleanup_job_resources(self, job_name: str):
        """清理作业相关资源"""
        namespace = CONFIG.CLUSTER.Kubernetes.NAMESPACE

        # 删除 Deployment
        try:
            await aio.to_thread(
                self.apps_v1.delete_namespaced_deployment,
                name=job_name,
                namespace=namespace,
            )
            LOGGER.info(f"Deleted Deployment: {job_name}")
        except ApiException as e:
            if e.status != 404:
                LOGGER.warning(f"Failed to delete deployment {job_name}: {e}")

        # 删除 Service
        try:
            await aio.to_thread(
                self.core_v1.delete_namespaced_service,
                name=f"{job_name}-svc",
                namespace=namespace,
            )
            LOGGER.info(f"Deleted Service: {job_name}-svc")
        except ApiException as e:
            if e.status != 404:
                LOGGER.warning(f"Failed to delete service {job_name}-svc: {e}")

    async def list_jobs(self) -> List[JobInfo]:
        """列出所有作业"""
        await self.ensure_initialized()

        # 构建标签选择器
        label_selectors = ["managed-by=yatcc-se", "type=code-server"]

        label_selector = ",".join(label_selectors)

        try:
            deployments = await aio.to_thread(
                self.apps_v1.list_namespaced_deployment,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                label_selector=label_selector,
            )

            jobs = []
            for deployment in deployments.items:
                container = deployment.spec.template.spec.containers[0]
                labels = deployment.metadata.labels or {}

                # 确定状态
                if (
                    deployment.status.ready_replicas
                    and deployment.status.ready_replicas >= 1
                ):
                    status = JobInfo.Status.RUNNING
                elif deployment.status.unavailable_replicas:
                    status = JobInfo.Status.FAILED
                else:
                    status = JobInfo.Status.PENDING

                user_id = labels.get("user-id")
                if user_id is not None:
                    user_id = str(user_id)

                job_info = JobInfo(
                    id=deployment.metadata.name,
                    name=deployment.metadata.name,
                    image=container.image,
                    ports=[CONFIG.CLUSTER.Codespace.PORT],
                    env={
                        env_var.name: env_var.value for env_var in (container.env or [])
                    },
                    status=status,
                    created_at=(
                        deployment.metadata.creation_timestamp.isoformat()
                        if deployment.metadata.creation_timestamp
                        else None
                    ),
                    namespace=deployment.metadata.namespace,
                    user_id=user_id,
                )
                jobs.append(job_info)

            return jobs

        except ApiException as e:
            raise ClusterError(f"Failed to list jobs: {e}")

    async def get_job_logs(self, job_name: str, lines: int = 100) -> str:
        """获取作业日志"""
        await self.ensure_initialized()
        try:
            # 获取关联的 Pod
            pods = await aio.to_thread(
                self.core_v1.list_namespaced_pod,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                label_selector=f"app={job_name}",
            )

            if not pods.items:
                raise JobNotFoundError(f"No pods found for job: {job_name}")

            # 获取第一个 Pod 的日志
            pod = pods.items[0]
            logs = await aio.to_thread(
                self.core_v1.read_namespaced_pod_log,
                name=pod.metadata.name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
                container="code-server",
                tail_lines=lines,
            )

            return logs

        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_name}")
            raise ClusterError(f"Failed to get job logs: {e}")
