"""Kubernetes 集群实现

专门针对用户独立的 code-server 镜像的部署和管理。
"""

import asyncio as aio
from base.logger import logger
from typing import Any, List, Dict
from kubernetes.client.rest import ApiException
from dataclasses import dataclass

from config import CONFIG, ENVIRON
from . import (
    ClusterABC,
    JobParams,
    JobInfo,
    ClusterError,
    JobNotFoundError,
    PortParams,
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
                "annotations": {
                    "yatcc-se/suspended": "true",
                    "yatcc-se/original-replicas": "1",  # 默认副本数为 1
                },
            },
            "spec": self._build_spec(),
        }

    def _build_service(self) -> Dict[str, Any]:
        """构建 Service 规格"""
        # 确保至少有一个端口信息
        if not self.job_params.ports:
            raise ValueError("JobParams must contain at least one port definition.")

        # 找到 http 端口，或者使用第一个端口作为默认

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
                        "name": port.name,
                        "port": port.port,  # 负载均衡器监听 80 端口 (标准HTTP)
                        "targetPort": port.target_port,  # 流量转发到容器的目标端口
                    }
                    for port in self.job_params.ports
                ],
                "type": "LoadBalancer",  # 关键修改：使用 LoadBalancer 类型以获取公网 IP
            },
        }

    def _build_spec(self) -> Dict[str, Any]:
        return {
            # 默认副本数为 0，在创建时不会自动启动
            "replicas": 0,
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
            "imagePullPolicy": "Always",
            "ports": [
                {"containerPort": item.target_port, "name": item.name}
                for item in self.job_params.ports
            ],
            "env": [{"name": k, "value": v} for k, v in self.job_params.env.items()],
            "args": [],
            "volumeMounts": self._build_volume_mounts(),
            "resources": self._build_resources(),
            # "readinessProbe": self._build_probe(),
            # "livenessProbe": self._build_probe(initial_delay=60, period=30),
        }

    def _build_volume_mounts(self) -> List[Dict[str, str]]:
        return [
            {"name": "code", "mountPath": "/code"},
            {"name": "io", "mountPath": "/io"},
            {"name": "root", "mountPath": "/data"},
        ]

    def _build_volumes(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "hostPath": {
                    "path": f"{CONFIG.CORE.students_dir}{self.job_params.user_id}/{name}",
                    "type": "DirectoryOrCreate",
                },
            }
            for name in ["code", "io", "root"]
        ]

    def _build_resources(self) -> Dict[str, Dict[str, str]]:
        return {
            "requests": {"memory": "1024Mi", "cpu": "500m"},
            "limits": {
                "memory": self.job_params.memory_limit
                or CONFIG.CLUSTER.Codespace.DEFAULT_MEMORY_LIMIT,
                "cpu": self.job_params.cpu_limit
                or CONFIG.CLUSTER.Codespace.DEFAULT_CPU_LIMIT,
            },
        }

    def _build_probe(self, initial_delay: int = 30, period: int = 10) -> Dict[str, Any]:
        return {
            "httpGet": {"path": "/", "port": 443},  # HTTP 健康检查路径
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

    async def allocate_resources(self, job_params: JobParams) -> JobInfo:
        """
        分配作业所需的资源 (Deployment 和 Service)，但不启动它。
        这是一个幂等操作：如果资源已存在，则直接返回其信息。
        """
        await self.ensure_initialized()

        job_name = job_params.name
        namespace = CONFIG.CLUSTER.Kubernetes.NAMESPACE

        try:
            # 1. 获取或创建 Deployment
            try:
                deployment = await aio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=job_name,
                    namespace=namespace,
                )
                LOGGER.info(f"Deployment '{job_name}' already exists.")
            except ApiException as e:
                if e.status == 404:
                    LOGGER.info(f"Deployment '{job_name}' not found, creating...")
                    deployment_spec = KubernetesSpec(job_params)._build_deployment()
                    deployment = await aio.to_thread(
                        self.apps_v1.create_namespaced_deployment,
                        namespace=namespace,
                        body=deployment_spec,
                    )
                    LOGGER.info(f"Successfully created Deployment '{job_name}'.")
                else:
                    raise  # 重新抛出其他 API 错误

            # 2. 获取或创建 Service
            service = await self._check_service(job_params)

            # 3. 返回代表已分配但暂停的资源的 JobInfo
            return await self._build_job_info(deployment, service)

        except Exception as e:
            LOGGER.error(f"Failed to allocate resources for job '{job_name}': {e}")
            raise ClusterError(f"Failed to allocate resources: {e}")

    async def submit_job(self, job_params: JobParams) -> JobInfo:
        """提交或更新 code-server 作业，并确保其运行。"""
        await self.ensure_initialized()

        # 步骤 1: 确保资源已分配。
        # 这一步是幂等的，如果资源已存在，它只会获取信息。
        await self.allocate_resources(job_params)

        # 步骤 2: 恢复或更新 Deployment，使其运行。
        return await self._resume_or_update_deployment(job_params)

    async def _resume_or_update_deployment(self, job_params: JobParams) -> JobInfo:
        """
        核心协调方法：恢复被暂停的 Deployment，并应用最新的配置。
        """
        job_name = job_params.name
        namespace = CONFIG.CLUSTER.Kubernetes.NAMESPACE
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # 读取最新的 Deployment
                deployment = await aio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=job_name,
                    namespace=namespace,
                )

                made_changes = False

                # 检查并恢复副本数
                annotations = deployment.metadata.annotations or {}
                if annotations.get("yatcc-se/suspended") == "true":
                    LOGGER.info(f"Resuming suspended Deployment '{job_name}'...")
                    replicas_str = annotations.get("yatcc-se/original-replicas", "1")
                    deployment.spec.replicas = int(replicas_str)
                    if "yatcc-se/suspended" in annotations:
                        del annotations["yatcc-se/suspended"]
                    if "yatcc-se/original-replicas" in annotations:
                        del annotations["yatcc-se/original-replicas"]
                    deployment.metadata.annotations = annotations
                    made_changes = True

                # 检查并更新容器配置
                container = deployment.spec.template.spec.containers[0]
                new_env = [{"name": k, "value": v} for k, v in job_params.env.items()]
                new_limits = {
                    "memory": job_params.memory_limit
                    or CONFIG.CLUSTER.Codespace.DEFAULT_MEMORY_LIMIT,
                    "cpu": job_params.cpu_limit
                    or CONFIG.CLUSTER.Codespace.DEFAULT_CPU_LIMIT,
                }
                if container.env != new_env or container.resources.limits != new_limits:
                    container.env = new_env
                    container.resources.limits = new_limits
                    made_changes = True

                # 如果有更改，则执行 patch
                if made_changes:
                    LOGGER.info(f"Patching Deployment '{job_name}' with updates...")
                    deployment = await aio.to_thread(
                        self.apps_v1.patch_namespaced_deployment,
                        name=job_name,
                        namespace=namespace,
                        body=deployment,
                    )
                else:
                    LOGGER.info(
                        f"Deployment '{job_name}' is already up-to-date and running."
                    )

                service = await self._check_service(job_params)
                return await self._build_job_info(deployment, service)

            except ApiException as e:
                if e.status == 409 and attempt < max_retries - 1:
                    LOGGER.warning(f"Conflict detected for '{job_name}'. Retrying...")
                    await aio.sleep(1)
                    continue
                raise ClusterError(
                    f"Failed to resume/update deployment '{job_name}': {e}"
                )

        raise ClusterError(
            f"Failed to resume/update deployment '{job_name}' after retries."
        )

    async def _check_service(self, job_params: JobParams):
        """确保 Service 存在，如果不存在则创建它，返回 Service 对象"""
        svc_name = job_params.name + "-svc"

        try:
            service = await aio.to_thread(
                self.core_v1.read_namespaced_service,
                name=svc_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )

            # Service 存在，返回 URL
            return service

        except ApiException as e:
            if e.status == 404:
                # Service 不存在，创建它
                LOGGER.info(f"Service '{svc_name}' not found, creating...")
                return await self._create_service(job_params)
            LOGGER.error(f"Failed to check service '{svc_name}': {e}")
            raise ClusterError(f"Failed to check service: {e}")

    async def _create_service(self, job_params: JobParams):
        """创建 Service，返回 Service 对象"""
        service_spec = KubernetesSpec(job_params)._build_service()
        svc_name = service_spec["metadata"]["name"]
        service = await aio.to_thread(
            self.core_v1.create_namespaced_service,
            namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            body=service_spec,
        )

        # 对于 LoadBalancer 类型，node_port 不再是关键信息，直接返回 service 对象
        return service

    async def get_service_url(self, job_name: str) -> str:
        """获取指定作业的外部可访问 URL"""
        await self.ensure_initialized()
        svc_name = f"{job_name}-svc"
        namespace = CONFIG.CLUSTER.Kubernetes.NAMESPACE

        try:
            service = await aio.to_thread(
                self.core_v1.read_namespaced_service,
                name=svc_name,
                namespace=namespace,
            )

            # 检查 LoadBalancer 的状态，等待公网 IP 分配
            if service.status.load_balancer and service.status.load_balancer.ingress:
                ingress_info = service.status.load_balancer.ingress[0]
                # 云服务商可能提供 IP 或 hostname
                external_ip = ingress_info.ip or ingress_info.hostname
                if external_ip:
                    # Service 的 port 被设置为 80，所以 URL 中不需要再指定端口号
                    return f"http://{external_ip}"

            # 如果没有分配 IP，说明负载均衡器还在创建中
            LOGGER.info(
                f"Service {svc_name} is waiting for an external IP from the LoadBalancer."
            )
            return "pending"

        except ApiException as e:
            if e.status == 404:
                LOGGER.warning(f"Service {svc_name} not found.")
                raise JobNotFoundError(f"Service not found for job: {job_name}")
            LOGGER.error(f"Failed to get service URL for {svc_name}: {e}")
            raise ClusterError(f"Failed to get service URL: {e}")

    async def get_job_status(self, job_name: str) -> JobInfo.Status:
        """获取作业状态"""
        await self.ensure_initialized()
        try:
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_name,
                namespace=CONFIG.CLUSTER.Kubernetes.NAMESPACE,
            )
            if not deployment:
                raise JobNotFoundError(f"Job not found: {job_name}")
            # 检查 Deployment 的状态
            if (
                deployment.status.ready_replicas
                and deployment.status.ready_replicas >= 1
            ):
                return JobInfo.Status.RUNNING
            elif deployment.status.unavailable_replicas:
                return JobInfo.Status.FAILED
            elif deployment.status.replicas == 0:
                return JobInfo.Status.SUSPENDED
            else:
                return JobInfo.Status.PENDING
        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_name}")
            raise ClusterError(f"Failed to get job status: {e}")

    async def get_job_info(self, job_name: str) -> JobInfo:
        """获取作业详细信息"""
        await self.ensure_initialized()
        namespace = CONFIG.CLUSTER.Kubernetes.NAMESPACE
        try:
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_name,
                namespace=namespace,
            )
            service = await aio.to_thread(
                self.core_v1.read_namespaced_service,
                name=f"{job_name}-svc",
                namespace=namespace,
            )
            return await self._build_job_info(deployment, service)
        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(
                    f"Job or associated service not found: {job_name}"
                )
            raise ClusterError(f"Failed to get job info: {e}")

    async def delete_job(self, job_name: str) -> None:
        """暂停指定的 Deployment (通过将副本数缩减到 0)"""
        await self.ensure_initialized()
        namespace = CONFIG.CLUSTER.Kubernetes.NAMESPACE
        max_retries = 3

        for attempt in range(max_retries):
            try:
                deployment = await aio.to_thread(
                    self.apps_v1.read_namespaced_deployment,
                    name=job_name,
                    namespace=namespace,
                )

                if deployment.spec.replicas == 0:
                    LOGGER.info(f"Deployment '{job_name}' is already suspended.")
                    return

                # 记录原始副本数并设置暂停注解
                annotations = deployment.metadata.annotations or {}
                annotations["yatcc-se/suspended"] = "true"
                annotations["yatcc-se/original-replicas"] = str(
                    deployment.spec.replicas or 1
                )
                deployment.metadata.annotations = annotations
                deployment.spec.replicas = 0

                await aio.to_thread(
                    self.apps_v1.patch_namespaced_deployment,
                    name=job_name,
                    namespace=namespace,
                    body=deployment,
                )
                LOGGER.info(f"Successfully suspended Deployment '{job_name}'.")
                return

            except ApiException as e:
                if e.status == 409 and attempt < max_retries - 1:
                    LOGGER.warning(
                        f"Conflict detected while suspending '{job_name}'. Retrying..."
                    )
                    await aio.sleep(1)
                    continue
                elif e.status == 404:
                    raise JobNotFoundError(
                        f"Cannot suspend: Deployment '{job_name}' not found."
                    )
                else:
                    raise ClusterError(
                        f"Failed to suspend deployment '{job_name}': {e}"
                    )

        raise ClusterError(f"Failed to suspend deployment '{job_name}' after retries.")

    async def _build_job_info(self, deployment, service) -> JobInfo:
        """从 Deployment 和 Service 对象构建 JobInfo"""
        annotations = deployment.metadata.annotations or {}
        if (
            annotations.get("yatcc-se/suspended") == "true"
            or deployment.spec.replicas == 0
        ):
            status = JobInfo.Status.SUSPENDED
        elif deployment.status.ready_replicas and deployment.status.ready_replicas >= 1:
            status = JobInfo.Status.RUNNING
        elif deployment.status.unavailable_replicas:
            status = JobInfo.Status.FAILED
        else:
            status = JobInfo.Status.PENDING

        service_url = "pending"
        if (
            service
            and service.status.load_balancer
            and service.status.load_balancer.ingress
        ):
            ingress_info = service.status.load_balancer.ingress[0]
            external_ip = ingress_info.ip or ingress_info.hostname
            if external_ip:
                service_url = f"http://{external_ip}"

        container = deployment.spec.template.spec.containers[0]
        labels = deployment.metadata.labels or {}
        user_id = labels.get("user-id")

        ports = [
            PortParams(
                name=item.name,
                port=item.port,
                target_port=item.target_port,
            )
            for item in (service.spec.ports if service else [])
        ]

        return JobInfo(
            id=deployment.metadata.name,
            name=deployment.metadata.name,
            image=container.image,
            ports=ports,
            env={env_var.name: env_var.value for env_var in (container.env or [])},
            status=status,
            created_at=(
                deployment.metadata.creation_timestamp.isoformat()
                if deployment.metadata.creation_timestamp
                else None
            ),
            namespace=deployment.metadata.namespace,
            service_url=service_url,
            user_id=str(user_id) if user_id else None,
        )

    async def cleanup_resources(self, job_name: str) -> None:
        """释放作业"""
        await self.ensure_initialized()
        try:
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
