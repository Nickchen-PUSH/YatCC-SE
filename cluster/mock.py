"""模拟集群实现

用于开发和测试环境。
"""

import asyncio as aio
import uuid
import logging
from datetime import datetime
from typing import Dict, List

from base import guard_ainit

from . import ClusterABC, JobParams, JobInfo, JobNotFoundError

logger = logging.getLogger(__name__)


class MockCluster(ClusterABC):
    """模拟集群实现"""

    def __init__(self):
        self._jobs: Dict[str, JobInfo] = {}
        self._initialized = False

    @guard_ainit(logger)
    async def initialize(self):
        """初始化集群连接"""
        self._initialized = True
        logger.info(f"Cluster {self.__class__.__name__} initialized")

    async def ensure_initialized(self):
        if not self._initialized:
            await self.initialize()

    async def allocate_resources(self, job_params):
        """创建模拟的 code-server 作业"""

        await self.ensure_initialized()

        # 验证必需参数
        if not job_params.user_id:
            raise ValueError("user_id is required")

        # 生成作业ID
        job_id = f"{job_params.user_id}"

        # 创建作业信息
        job_info = JobInfo(
            id=job_id,
            name=job_params.name,
            image=job_params.image,
            ports=job_params.ports,
            env=job_params.env,
            status=JobInfo.Status.PENDING,
            created_at=datetime.now().isoformat(),
            namespace="default",
            service_url=f"http://mock-service-{job_id}:8080",
            user_id=job_params.user_id,
        )

        # 存储作业
        self._jobs[job_params.name] = job_info

        # 模拟异步启动
        aio.create_task(self._simulate_job_lifecycle(job_params.name))

        logger.info(f"Mock code-server job submitted: {job_params.name}")
        return job_info

    async def submit_job(self, job_params: JobParams) -> JobInfo:
        """提交模拟的 code-server 作业"""
        await self.ensure_initialized()

        # 验证必需参数
        if not job_params.user_id:
            raise ValueError("user_id is required")

        # 生成作业ID
        job_id = f"codespace-{job_params.user_id}"

        # 创建作业信息
        job_info = JobInfo(
            id=job_id,
            name=job_params.name,
            image=job_params.image,
            ports=job_params.ports,
            env=job_params.env,
            status=JobInfo.Status.PENDING,
            created_at=datetime.now().isoformat(),
            namespace="default",
            service_url=f"http://mock-service-{job_id}:8080",
            user_id=job_params.user_id,
        )

        # 存储作业
        self._jobs[job_params.name] = job_info

        # 模拟异步启动
        aio.create_task(self._simulate_job_lifecycle(job_params.name))

        logger.info(f"Mock code-server job submitted: {job_params.name}")
        return job_info

    async def _simulate_job_lifecycle(self, job_id: str):
        """模拟作业生命周期"""
        await aio.sleep(0.003)  # 模拟启动延迟

        if job_id in self._jobs:
            self._jobs[job_id].status = JobInfo.Status.RUNNING
            self._jobs[job_id].updated_at = datetime.now().isoformat()
            logger.info(f"Mock code-server job running: {job_id}")

    async def get_job_status(self, job_id: str) -> JobInfo.Status:
        """获取模拟作业状态"""
        await self.ensure_initialized()

        if job_id not in self._jobs:
            raise JobNotFoundError(f"Job not found: {job_id}")

        return self._jobs[job_id].status

    async def get_job_info(self, job_id: str) -> JobInfo:
        """获取模拟作业信息"""
        await self.ensure_initialized()

        if job_id not in self._jobs:
            raise JobNotFoundError(f"Job not found: {job_id}")

        return self._jobs[job_id].copy(deep=True)

    async def get_service_url(self, job_id: str) -> str:
        """获取模拟作业的服务访问地址"""
        await self.ensure_initialized()

        if job_id not in self._jobs:
            raise JobNotFoundError(f"Job not found: {job_id}")

        return self._jobs[job_id].service_url

    async def delete_job(self, job_id: str) -> None:
        """删除模拟作业"""
        await self.ensure_initialized()

        if job_id not in self._jobs:
            raise JobNotFoundError(f"Job not found: {job_id}")

        del self._jobs[job_id]
        logger.info(f"Mock code-server job deleted: {job_id}")

    async def list_jobs(self) -> List[JobInfo]:
        """列出所有模拟作业"""
        await self.ensure_initialized()

        jobs = []
        for job_info in self._jobs.values():
            # 过滤条件
            jobs.append(job_info.copy(deep=True))

        return jobs

    async def get_job_logs(self, job_id: str, lines: int = 100) -> str:
        """获取模拟作业日志"""
        await self.ensure_initialized()

        if job_id not in self._jobs:
            raise JobNotFoundError(f"Job not found: {job_id}")

        # 生成模拟日志
        logs = []
        for i in range(min(lines, 20)):
            timestamp = datetime.now().isoformat()
            logs.append(
                f"{timestamp} [INFO] Mock code-server log line {i+1} for job {job_id}"
            )

        return "\n".join(logs)

    async def cleanup_resources(self, job_name: str = None):
        """清理模拟资源"""
        await super().cleanup_resources(job_name)
        if job_name:
            if job_name in self._jobs:
                del self._jobs[job_name]
                logger.info(f"Mock cluster job {job_name} cleaned up")
            else:
                logger.warning(f"Mock cluster job {job_name} not found for cleanup")
        else:
            self._jobs.clear()
        logger.info("Mock cluster {job_name} cleaned up")
