"""底层平台接口层模块

提供统一的集群管理接口。目前仅支持部署 code-server。
"""

import asyncio as aio
import logging
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from config import CONFIG, ClusterConfig

from base import guard_ainit

logger = logging.getLogger(__name__)

class JobParams(BaseModel):
    """作业参数"""
    name: str = Field(..., description="作业名称")
    image: str = Field(default="codercom/code-server:latest", description="镜像名称")
    ports: List[int] = Field(default_factory=lambda: [8080], description="端口映射")
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
    ports: List[int] = Field(default_factory=list, description="端口映射")
    env: Dict[str, str] = Field(default_factory=dict, description="环境变量")
    status: int = Field(..., description="作业状态")
    
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    namespace: Optional[str] = Field(None, description="命名空间")
    service_url: Optional[str] = Field(None, description="服务访问地址")
    
    # 用户信息
    user_id: Optional[int] = Field(None, description="用户ID")
    
    class Status(IntEnum):
        PENDING = 0
        RUNNING = 1
        SUCCESS = 2
        FAILED = 3
        STOPPING = 4
        STOPPED = 5


class ClusterABC(ABC):
    """集群接口基类"""

    def __init__(self, config: ClusterConfig = None):
        self.config = config or ClusterConfig()
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
    async def allocate_resources(self, job_params: JobParams) -> JobInfo:
        """创建作业（分配一个 deployment）"""
        pass

    @abstractmethod
    async def submit_job(self, job_params: JobParams) -> JobInfo:
        """提交作业"""
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> JobInfo.Status:
        """获取作业状态"""
        pass

    @abstractmethod
    async def get_job_info(self, job_id: str) -> JobInfo:
        """获取作业信息"""
        pass

    @abstractmethod
    async def delete_job(self, job_id: str) -> None:
        """删除作业"""
        pass

    @abstractmethod
    async def list_jobs(self) -> List[JobInfo]:
        """列出作业"""
        pass

    @abstractmethod
    async def get_job_logs(self, job_id: str, lines: int = 100) -> str:
        """获取作业日志"""
        pass

    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        logger.info(f"Cluster {self.__class__.__name__} cleanup")


# 异常定义
class ClusterError(Exception):
    """集群操作异常"""
    pass


class JobNotFoundError(ClusterError):
    """作业不存在异常"""
    pass


def create(type:str = "mock", config = CONFIG) -> ClusterABC:
    """创建集群实例"""
    if type == "mock":
        from .mock import MockCluster
        return MockCluster(config)
    elif type == "kubernetes":
        from .kubernetes import KubernetesCluster
        return KubernetesCluster(config)
    else:
        raise ValueError(f"Unsupported cluster type: {type}")


def create_code_server_job(user_id: str, **kwargs) -> JobParams:
    """创建 code-server 作业参数的便捷函数"""
    config = CONFIG.CLUSTER.Codespace
    
    return JobParams(
        name=user_id,
        image=config.IMAGE,
        ports=[config.PORT],
        env={
            "PASSWORD": f"student{user_id}",
            "SUDO_PASSWORD": f"student{user_id}",
            **kwargs.get("env", {})
        },
        user_id=user_id,
        cpu_limit=kwargs.get("cpu_limit", config.DEFAULT_CPU_LIMIT),
        memory_limit=kwargs.get("memory_limit", config.DEFAULT_MEMORY_LIMIT),
        storage_size=kwargs.get("storage_size", config.DEFAULT_STORAGE_SIZE)
    )