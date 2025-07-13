"""底层平台接口层模块

提供统一的集群管理接口。目前仅支持部署 code-server。
"""

import asyncio as aio
import logging
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from config import CONFIG, ClusterConfig


from base import guard_ainit

logger = logging.getLogger(__name__)


class PortParams(BaseModel):
    """端口参数"""

    port: int = Field(..., description="端口号")
    target_port: Optional[int] = Field(None, description="目标端口")
    name: Optional[str] = Field(None, description="端口名称")
    protocol: str = Field(default="TCP", description="协议类型，默认为 TCP")
    node_port: Optional[int] = Field(None, description="节点端口（用于 NodePort 服务）")

    @staticmethod
    def from_config(config: Dict[str, Any]) -> "PortParams":
        """从配置字典创建 PortParams 实例"""
        return PortParams(
            port=config.get("port"),
            target_port=config.get("targetPort"),
            name=config.get("name"),
            protocol=config.get("protocol", "TCP"),
            node_port=config.get("nodePort"),
        )


class JobParams(BaseModel):
    """作业参数"""

    name: str = Field(..., description="作业名称")
    image: str = Field(default="codercom/code-server:latest", description="镜像名称")
    ports: List[PortParams] = Field(default_factory=list, description="端口映射列表")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")

    # 资源限制
    cpu_limit: Optional[str] = Field(None, description="CPU限制，如 '1000m'")
    memory_limit: Optional[str] = Field(None, description="内存限制，如 '2Gi'")
    storage_size: Optional[str] = Field(None, description="存储大小，如 '5Gi'")

    # 用户信息（用于隔离）
    user_id: str = Field(..., description="用户ID")


class JobInfo(BaseModel):
    """作业信息"""

    id: str = Field(..., description="作业ID")
    name: str = Field(..., description="作业名称")
    image: str = Field(..., description="镜像名称")
    ports: List[PortParams] = Field(default_factory=list, description="端口映射列表")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    status: int = Field(..., description="作业状态")

    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    namespace: Optional[str] = Field(None, description="命名空间")
    service_url: Optional[str] = Field(None, description="服务访问地址")

    # 用户信息
    user_id: Optional[str] = Field(None, description="用户ID")

    class Status(IntEnum):
        PENDING = 0
        RUNNING = 1
        FAILED = 2
        SUSPENDED = 3
        STARTING = 4


def _read_port_config() -> List[PortParams]:
    """读取端口配置"""
    ports = []
    for port in CONFIG.CLUSTER.Codespace.PORTS:
        ports.append(PortParams(**port))
    return ports


class ClusterABC(ABC):
    """集群接口基类"""

    def __init__(self):
        self._initialized = False

    @guard_ainit(logger)
    async def initialize(self):
        """初始化集群连接"""
        self._initialized = True
        logger.info(f"Cluster {self.__class__.__name__} initialized")

    async def ensure_initialized(self):
        if not self._initialized:
            await self.initialize()

    @abstractmethod
    async def submit_job(self, job_params: JobParams) -> JobInfo:
        """提交作业"""
        pass

    @abstractmethod
    async def get_job_status(self, job_name: str) -> JobInfo.Status:
        """获取作业状态"""
        pass

    @abstractmethod
    async def get_job_info(self, job_name: str) -> JobInfo:
        """获取作业信息"""
        pass

    @abstractmethod
    async def delete_job(self, job_name: str) -> None:
        """删除作业"""
        pass

    @abstractmethod
    async def list_jobs(self) -> List[JobInfo]:
        """列出作业"""
        pass

    @abstractmethod
    async def get_job_logs(self, job_name: str, lines: int = 100) -> str:
        """获取作业日志"""
        pass

    @abstractmethod
    async def allocate_resources(self, job_params: JobParams) -> JobInfo:
        """分配计算资源"""
        pass

    @abstractmethod
    async def cleanup_resources(self, job_name: str):
        """回收计算资源"""
        logger.info(f"Cluster {self.__class__.__name__} cleanup")


# 异常定义
class ClusterError(Exception):
    """集群操作异常"""

    pass


class JobNotFoundError(ClusterError):
    """作业不存在异常"""

    pass


def create(type: str = "mock") -> ClusterABC:
    """创建集群实例"""
    if type == "mock":
        from .mock import MockCluster

        return MockCluster()
    elif type == "kubernetes":
        from .kubernetes import KubernetesCluster

        return KubernetesCluster()
    else:
        raise ValueError(f"Unsupported cluster type: {type}")
