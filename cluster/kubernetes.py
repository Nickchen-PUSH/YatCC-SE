"""Kubernetes 集群实现

code-server 镜像的部署和管理。
"""

import asyncio as aio
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from kubernetes import client, config
from kubernetes.client.rest import ApiException

from . import (
    ClusterABC, JobParams, JobInfo, ClusterConfig,
    ClusterError, JobNotFoundError
)

logger = logging.getLogger(__name__)


class KubernetesCluster(ClusterABC):
    """Kubernetes 集群实现"""

    def __init__(self, config=None):
        super().__init__(config)
        self._k8s_client = None
        self._apps_v1 = None
        self._core_v1 = None
        self._networking_v1 = None
        self._is_initialized = False
    
    async def initialize(self):
        """初始化 Kubernetes 集群连接"""
        if self._is_initialized:
            return
        
        try:
            # 导入 Kubernetes 客户端
            from kubernetes import client, config as k8s_config
            from kubernetes.client.rest import ApiException
            
            # 尝试加载配置
            try:
                if self.config.Kubernetes.KUBECONFIG_PATH:
                    k8s_config.load_kube_config(config_file=self.config.Kubernetes.KUBECONFIG_PATH)
                else:
                    # 尝试自动加载配置
                    k8s_config.load_kube_config()
                logger.info("Loaded kubeconfig from file")
            except Exception:
                try:
                    # 如果在集群内，尝试加载集群内配置
                    k8s_config.load_incluster_config()
                    logger.info("Loaded in-cluster config")
                except Exception as e:
                    raise ClusterError(f"Failed to load Kubernetes config: {e}")
            
            # 创建客户端
            self._k8s_client = client.ApiClient()
            self._apps_v1 = client.AppsV1Api()
            self._core_v1 = client.CoreV1Api()
            self._networking_v1 = client.NetworkingV1Api()
            
            # 测试连接
            await aio.to_thread(self._core_v1.list_namespace, timeout_seconds=10)
            
            self._is_initialized = True
            logger.info("Kubernetes cluster initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes cluster: {e}")
            raise ClusterError(f"Kubernetes initialization failed: {e}")

    async def submit_job(self, job_params: JobParams) -> JobInfo:
        """提交 code-server 作业到 Kubernetes"""
        await self.ensure_initialized()

        # 验证必需参数
        if not job_params.user_id:
            raise ValueError("user_id is required")
        
        # 生成唯一作业名称
        job_name = self._generate_job_name(job_params)
        
        try:
            # 创建持久化存储
            await self._create_pvc(job_name, job_params)
            
            # 创建 Deployment
            await self._create_deployment(job_name, job_params)
            
            # 创建 Service
            service_url = await self._create_service(job_name, job_params)
            
            return JobInfo(
                id=job_name,
                name=job_params.name,
                image=job_params.image,
                ports=job_params.ports,
                env=job_params.env,
                status=JobInfo.Status.PENDING,
                created_at=datetime.now().isoformat(),
                namespace=self.config.Kubernetes.NAMESPACE,
                service_url=service_url,
                user_id=job_params.user_id,
            )
            
        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            # 清理可能创建的资源
            await self._cleanup_job_resources(job_name)
            raise ClusterError(f"Failed to submit job: {e}")

    def _generate_job_name(self, job_params: JobParams) -> str:
        """生成作业名称"""
        base_name = f"codeserver-{job_params.user_id}"
        return f"{base_name}-{uuid.uuid4().hex[:6]}"

    async def _create_pvc(self, job_name: str, job_params: JobParams):
        """创建持久化存储卷"""
        pvc_spec = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": f"{job_name}-pvc",
                "labels": self._build_labels(job_params),
                "namespace": self.config.Kubernetes.NAMESPACE
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "resources": {
                    "requests": {
                        "storage": job_params.storage_size or self.config.CodeServer.DEFAULT_STORAGE_SIZE
                    }
                }
            }
        }
        
        await aio.to_thread(
            self.core_v1.create_namespaced_persistent_volume_claim,
            namespace=self.config.Kubernetes.NAMESPACE,
            body=pvc_spec
        )
        logger.info(f"Created PVC: {job_name}-pvc")

    async def _create_deployment(self, job_name: str, job_params: JobParams):
        """创建 Deployment"""
        # 合并默认环境变量
        env_vars = {
            "PASSWORD": job_params.env.get("PASSWORD", f"student{job_params.user_id}"),
            "SUDO_PASSWORD": job_params.env.get("SUDO_PASSWORD", f"student{job_params.user_id}"),
            **job_params.env
        }
        
        deployment_spec = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": job_name,
                "labels": self._build_labels(job_params),
                "namespace": self.config.Kubernetes.NAMESPACE
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {"app": job_name}
                },
                "template": {
                    "metadata": {
                        "labels": {"app": job_name, **self._build_labels(job_params)}
                    },
                    "spec": {
                        "containers": [{
                            "name": "code-server",
                            "image": job_params.image,
                            "ports": [{"containerPort": self.config.CodeServer.PORT}],
                            "env": [{"name": k, "value": v} for k, v in env_vars.items()],
                            "args": [
                                "--bind-addr=0.0.0.0:8080",
                                "--auth=password",
                                "--disable-telemetry",
                                "/workspace"
                            ],
                            "volumeMounts": [{
                                "name": "workspace",
                                "mountPath": "/workspace"
                            }],
                            "resources": {
                                "requests": {
                                    "memory": "256Mi",
                                    "cpu": "250m"
                                },
                                "limits": {
                                    "memory": job_params.memory_limit or self.config.CodeServer.DEFAULT_MEMORY_LIMIT,
                                    "cpu": job_params.cpu_limit or self.config.CodeServer.DEFAULT_CPU_LIMIT
                                }
                            },
                            "readinessProbe": {
                                "httpGet": {
                                    "path": "/",
                                    "port": self.config.CodeServer.PORT
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10
                            },
                            "livenessProbe": {
                                "httpGet": {
                                    "path": "/",
                                    "port": self.config.CodeServer.PORT
                                },
                                "initialDelaySeconds": 60,
                                "periodSeconds": 30
                            }
                        }],
                        "volumes": [{
                            "name": "workspace",
                            "persistentVolumeClaim": {
                                "claimName": f"{job_name}-pvc"
                            }
                        }],
                        "restartPolicy": "Always"
                    }
                }
            }
        }
        
        await aio.to_thread(
            self.apps_v1.create_namespaced_deployment,
            namespace=self.config.Kubernetes.NAMESPACE,
            body=deployment_spec
        )
        logger.info(f"Created Deployment: {job_name}")

    async def _create_service(self, job_name: str, job_params: JobParams) -> str:
        """创建 Service"""
        service_spec = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{job_name}-svc",
                "labels": self._build_labels(job_params),
                "namespace": self.config.Kubernetes.NAMESPACE
            },
            "spec": {
                "selector": {"app": job_name},
                "ports": [{
                    "port": self.config.CodeServer.PORT,
                    "targetPort": self.config.CodeServer.PORT,
                    "protocol": "TCP",
                    "name": "http"
                }],
                "type": "ClusterIP"
            }
        }
        
        await aio.to_thread(
            self.core_v1.create_namespaced_service,
            namespace=self.config.Kubernetes.NAMESPACE,
            body=service_spec
        )
        
        service_url = f"http://{job_name}-svc.{self.config.Kubernetes.NAMESPACE}.svc.cluster.local:{self.config.CodeServer.PORT}"
        logger.info(f"Created Service: {job_name}-svc")
        return service_url

    def _build_labels(self, job_params: JobParams) -> Dict[str, str]:
        """构建标签"""
        return {
            "managed-by": "yatcc-se",
            "user-id": str(job_params.user_id),
            "type": "code-server"
        }

    async def get_job_status(self, job_id: str) -> JobInfo.Status:
        """获取作业状态"""
        await self.ensure_initialized()
        
        try:
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_id,
                namespace=self.config.Kubernetes.NAMESPACE
            )
            
            # 检查 Deployment 状态
            if deployment.status.ready_replicas and deployment.status.ready_replicas >= 1:
                return JobInfo.Status.RUNNING
            elif deployment.status.unavailable_replicas:
                return JobInfo.Status.FAILED
            else:
                return JobInfo.Status.PENDING
                
        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_id}")
            raise ClusterError(f"Failed to get job status: {e}")

    async def get_job_info(self, job_id: str) -> JobInfo:
        """获取作业详细信息"""
        await self.ensure_initialized()
        
        try:
            deployment = await aio.to_thread(
                self.apps_v1.read_namespaced_deployment,
                name=job_id,
                namespace=self.config.Kubernetes.NAMESPACE
            )
            
            container = deployment.spec.template.spec.containers[0]
            labels = deployment.metadata.labels or {}
            
            # 确定状态
            if deployment.status.ready_replicas and deployment.status.ready_replicas >= 1:
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
                    name=f"{job_id}-svc",
                    namespace=self.config.Kubernetes.NAMESPACE
                )
                service_url = f"http://{service.metadata.name}.{service.metadata.namespace}.svc.cluster.local:{self.config.CodeServer.PORT}"
            except ApiException:
                pass
            
            return JobInfo(
                id=deployment.metadata.name,
                name=deployment.metadata.labels.get("app", deployment.metadata.name),
                image=container.image,
                ports=[self.config.CodeServer.PORT],
                env={env_var.name: env_var.value for env_var in (container.env or [])},
                status=status,
                created_at=deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None,
                namespace=deployment.metadata.namespace,
                service_url=service_url,
                user_id=int(labels.get("user-id", 0)) if labels.get("user-id") else None,
            )
            
        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_id}")
            raise ClusterError(f"Failed to get job info: {e}")

    async def delete_job(self, job_id: str) -> None:
        """删除作业"""
        await self.ensure_initialized()
        
        try:
            await self._cleanup_job_resources(job_id)
            logger.info(f"Job deleted: {job_id}")
        except ApiException as e:
            if e.status != 404:
                raise ClusterError(f"Failed to delete job: {e}")

    async def _cleanup_job_resources(self, job_name: str):
        """清理作业相关资源"""
        namespace = self.config.Kubernetes.NAMESPACE
        
        # 删除 Deployment
        try:
            await aio.to_thread(
                self.apps_v1.delete_namespaced_deployment,
                name=job_name,
                namespace=namespace
            )
            logger.info(f"Deleted Deployment: {job_name}")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Failed to delete deployment {job_name}: {e}")
        
        # 删除 Service
        try:
            await aio.to_thread(
                self.core_v1.delete_namespaced_service,
                name=f"{job_name}-svc",
                namespace=namespace
            )
            logger.info(f"Deleted Service: {job_name}-svc")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Failed to delete service {job_name}-svc: {e}")
        
        # 删除 PVC
        try:
            await aio.to_thread(
                self.core_v1.delete_namespaced_persistent_volume_claim,
                name=f"{job_name}-pvc",
                namespace=namespace
            )
            logger.info(f"Deleted PVC: {job_name}-pvc")
        except ApiException as e:
            if e.status != 404:
                logger.warning(f"Failed to delete PVC {job_name}-pvc: {e}")

    async def list_jobs(self) -> List[JobInfo]:
        """列出所有作业"""
        await self.ensure_initialized()
        
        # 构建标签选择器
        label_selectors = ["managed-by=yatcc-se", "type=code-server"]
        
        label_selector = ",".join(label_selectors)
        
        try:
            deployments = await aio.to_thread(
                self.apps_v1.list_namespaced_deployment,
                namespace=self.config.Kubernetes.NAMESPACE,
                label_selector=label_selector
            )
            
            jobs = []
            for deployment in deployments.items:
                container = deployment.spec.template.spec.containers[0]
                labels = deployment.metadata.labels or {}
                
                # 确定状态
                if deployment.status.ready_replicas and deployment.status.ready_replicas >= 1:
                    status = JobInfo.Status.RUNNING
                elif deployment.status.unavailable_replicas:
                    status = JobInfo.Status.FAILED
                else:
                    status = JobInfo.Status.PENDING
                
                job_info = JobInfo(
                    id=deployment.metadata.name,
                    name=deployment.metadata.labels.get("app", deployment.metadata.name),
                    image=container.image,
                    ports=[self.config.CodeServer.PORT],
                    env={env_var.name: env_var.value for env_var in (container.env or [])},
                    status=status,
                    created_at=deployment.metadata.creation_timestamp.isoformat() if deployment.metadata.creation_timestamp else None,
                    namespace=deployment.metadata.namespace,
                    user_id=int(labels.get("user-id", 0)) if labels.get("user-id") else None,
                )
                jobs.append(job_info)
            
            return jobs
            
        except ApiException as e:
            raise ClusterError(f"Failed to list jobs: {e}")

    async def get_job_logs(self, job_id: str, lines: int = 100) -> str:
        """获取作业日志"""
        await self.ensure_initialized()
        
        try:
            # 获取关联的 Pod
            pods = await aio.to_thread(
                self.core_v1.list_namespaced_pod,
                namespace=self.config.Kubernetes.NAMESPACE,
                label_selector=f"app={job_id}"
            )
            
            if not pods.items:
                raise JobNotFoundError(f"No pods found for job: {job_id}")
            
            # 获取第一个 Pod 的日志
            pod = pods.items[0]
            logs = await aio.to_thread(
                self.core_v1.read_namespaced_pod_log,
                name=pod.metadata.name,
                namespace=self.config.Kubernetes.NAMESPACE,
                container="code-server",
                tail_lines=lines
            )
            
            return logs
            
        except ApiException as e:
            if e.status == 404:
                raise JobNotFoundError(f"Job not found: {job_id}")
            raise ClusterError(f"Failed to get job logs: {e}")