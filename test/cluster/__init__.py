"""cluster 模块测试包

提供 cluster 模块的完整测试覆盖，专注于用户独立的 code-server 部署。
"""

import asyncio as aio
import sys
import traceback
from cluster import create, JobParams, create_code_server_job, JobInfo
from base.logger import logger
from .. import AsyncTestCase, RUNNER, setup_test, guard_once

LOGGER = logger(__spec__, __file__)

# 测试用集群实例
_TEST_CLUSTER = None
_KUBERNETES_CLUSTER = None


@guard_once
async def ainit_test_cluster():
    """初始化测试用集群"""
    global _TEST_CLUSTER
    
    try:
        LOGGER.info("Initializing test cluster...")
        
        # 创建 Mock 集群用于基础测试
        _TEST_CLUSTER = create(type="mock")
        await _TEST_CLUSTER.initialize()
        
        LOGGER.info(f"Test cluster initialized: {_TEST_CLUSTER.__class__.__name__}")
        return _TEST_CLUSTER
        
    except Exception as e:
        LOGGER.error(f"Failed to initialize test cluster: {e}")
        LOGGER.error(f"Traceback: {traceback.format_exc()}")
        return None


@guard_once
async def ainit_kubernetes_cluster():
    """初始化 Kubernetes 测试集群"""
    global _KUBERNETES_CLUSTER
    
    try:
        LOGGER.info("Initializing Kubernetes test cluster...")
        
        # 连接 Kubernetes
        _KUBERNETES_CLUSTER = create(type="kubernetes")
        await _KUBERNETES_CLUSTER.initialize()
        
        LOGGER.info(f"Kubernetes test cluster initialized: {_KUBERNETES_CLUSTER.__class__.__name__}")
        return _KUBERNETES_CLUSTER
        
    except Exception as e:
        LOGGER.error(f"Failed to initialize Kubernetes cluster: {e}")
        LOGGER.error(f"Traceback: {traceback.format_exc()}")
        return None


def setUpModule() -> None:
    """模块级别的设置"""
    try:
        LOGGER.info("Setting up cluster test module...")
        setup_test(__name__)
        
        # 初始化两个集群
        RUNNER.run(ainit_test_cluster())
        RUNNER.run(ainit_kubernetes_cluster())
        
        LOGGER.info("Cluster test module setup completed")
    except Exception as e:
        LOGGER.error(f"Module setup failed: {e}")
        LOGGER.error(f"Traceback: {traceback.format_exc()}")


def tearDownModule() -> None:
    """模块级别的清理"""
    global _TEST_CLUSTER, _KUBERNETES_CLUSTER
    
    async def cleanup():
        try:
            if _TEST_CLUSTER:
                await _TEST_CLUSTER.cleanup()
                LOGGER.info("Test cluster cleaned up")
            if _KUBERNETES_CLUSTER:
                await _KUBERNETES_CLUSTER.cleanup()
                LOGGER.info("Kubernetes cluster cleaned up")
        except Exception as e:
            LOGGER.warning(f"Cleanup error: {e}")
    
    try:
        RUNNER.run(cleanup())
        LOGGER.info("Cluster test module cleanup completed")
    except Exception as e:
        LOGGER.warning(f"Module cleanup error: {e}")


class ClusterTestBase(AsyncTestCase):
    """集群测试基类
    
    提供集群测试的通用功能和工具方法。
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_jobs = []  # 跟踪创建的作业，用于清理
    
    def setUp(self) -> None:
        """测试方法设置"""
        self.created_jobs = []
        self.cluster = get_test_cluster()
        
        if self.cluster is None:
            LOGGER.warning("Test cluster is None, creating temporary cluster")
            try:
                temp_cluster = create(type="mock")
                RUNNER.run(temp_cluster.initialize())
                self.cluster = temp_cluster
                global _TEST_CLUSTER
                _TEST_CLUSTER = temp_cluster
                LOGGER.info("Temporary test cluster created")
            except Exception as e:
                LOGGER.error(f"Failed to create temporary cluster: {e}")
        
        self.assertIsNotNone(self.cluster, "Test cluster should be available")
    
    def tearDown(self) -> None:
        """测试方法清理"""
        if self.cluster and self.created_jobs:
            async def cleanup_jobs():
                for job_id in self.created_jobs:
                    try:
                        await self.cluster.delete_job(job_id)
                        LOGGER.debug(f"Cleaned up job: {job_id}")
                    except Exception as e:
                        LOGGER.warning(f"Failed to cleanup job {job_id}: {e}")
            
            try:
                RUNNER.run(cleanup_jobs())
            except Exception as e:
                LOGGER.warning(f"Job cleanup error: {e}")
            
            self.created_jobs.clear()
    
    def track_job(self, job_id: str):
        """跟踪创建的作业，用于自动清理"""
        self.created_jobs.append(job_id)
    
    def create_test_job_params(self, name: str = "test-job", **kwargs) -> JobParams:
        """创建测试用的作业参数"""
        import time
        default_params = {
            "name": f"{name}-{int(time.time() % 10000)}",
            "image": "codercom/code-server:latest",
            "ports": [8080],
            "env": {"TEST": "true", "TIMESTAMP": str(int(time.time()))},
            "user_id": kwargs.get("user_id", 1001),
        }
        default_params.update(kwargs)
        return JobParams(**default_params)
    
    def create_code_server_params(self, user_id: int, workspace_name: str = None, **kwargs) -> JobParams:
        """创建用户独立的 code-server 作业参数"""
        return create_code_server_job(user_id=user_id, workspace_name=workspace_name, **kwargs)
    
    async def wait_for_job_status(self, job_id: str, target_status, timeout: int = 30):
        """等待作业达到指定状态"""
        start_time = aio.get_event_loop().time()
        
        while (aio.get_event_loop().time() - start_time) < timeout:
            try:
                status = await self.cluster.get_job_status(job_id)
                if status == target_status:
                    return True
            except Exception:
                pass
            
            await aio.sleep(1)
        
        return False
    
    def assert_job_info_valid(self, job_info):
        """验证作业信息的有效性"""
        self.assertIsInstance(job_info, JobInfo)
        self.assertIsNotNone(job_info.id)
        self.assertIsNotNone(job_info.name)
        self.assertIsNotNone(job_info.image)
        self.assertIsInstance(job_info.ports, list)
        self.assertIsInstance(job_info.env, dict)
        # 验证用户独立部署的必须字段
        self.assertIsNotNone(job_info.user_id)
    
    def assert_code_server_job_valid(self, job_info):
        """验证 code-server 作业的特殊要求"""
        self.assert_job_info_valid(job_info)
        self.assertEqual(job_info.image, "codercom/code-server:latest")
        self.assertIn(8080, job_info.ports)
        self.assertIn("PASSWORD", job_info.env)
    
    def assert_user_isolation(self, job_info, expected_user_id: int):
        """验证用户隔离"""
        self.assertEqual(job_info.user_id, expected_user_id)
        # 验证作业名称包含用户标识
        self.assertIn(f"{expected_user_id}", job_info.name)


def get_test_cluster():
    """获取测试集群实例"""
    return _TEST_CLUSTER


def get_kubernetes_cluster():
    """获取 Kubernetes 测试集群实例"""
    return _KUBERNETES_CLUSTER