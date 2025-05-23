"""底层平台接口层模块"""

from abc import ABC, abstractmethod
from enum import IntEnum

from pydantic import BaseModel, Field
class ImageInfo(BaseModel):
    """镜像信息模型"""
    id: str = Field(..., description="镜像ID")
    name: str = Field(..., description="镜像名称")
    description: str = Field(..., description="镜像描述")
    full_name: str = Field(..., description="镜像全名")

class JobParams(BaseModel):
    """作业参数模型"""
    name: str = Field(..., description="作业名称")
    image: str = Field(..., description="镜像名称")
    ports: list[int] = Field(..., description="端口映射")
    env: dict[str, str] = Field(..., description="环境变量")

class JobInfo(BaseModel):
    """作业信息模型"""
    id: str = Field(..., description="作业ID")
    name: str = Field(..., description="作业名称")
    image: str = Field(..., description="镜像名称")
    ports: list[int] = Field(..., description="端口映射")
    env: dict[str, str] = Field(..., description="环境变量")
    class Status(IntEnum):
        """作业状态枚举类"""
        PENDING = 0
        RUNNING = 1
        SUCCESS = 2
        FAILED = 3


class ClusterABC(ABC):
    """集群接口基类"""

    class JobStatus(IntEnum):
        """作业状态枚举类"""
        PENDING = 0
        RUNNING = 1
        SUCCESS = 2
        FAILED = 3

    @abstractmethod
    def submit_job(self, job_params: JobParams) -> JobInfo:
        """提交作业"""
        pass

    @abstractmethod
    def get_job_status(self, job_id: str) -> JobStatus:
        """获取作业状态"""
        pass

    @abstractmethod
    def get_image_info(self, image_id: str) -> ImageInfo:
        """获取镜像信息"""
        pass

    @abstractmethod
    def delete_job(self, job_id: str) -> None:
        """删除作业"""
        pass

    @abstractmethod
    def list_jobs(self) -> list[JobInfo]:
        """列出所有作业"""
        pass

    @abstractmethod
    def list_images(self) -> list[ImageInfo]:
        """列出所有镜像"""
        pass
    