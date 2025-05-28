"""cluster 模块测试包

提供 cluster 模块的完整测试覆盖，专注于用户独立的 code-server 部署。
"""

import asyncio as aio
import sys
import traceback
import time
from pathlib import Path
from cluster import JobParams, JobInfo, create

# 确保项目根目录在路径中

def create_code_server_job(user_id: int, workspace_name: str = None, **kwargs) -> JobParams:
    """创建用户独立的 code-server 作业参数"""
    if workspace_name is None:
        workspace_name = f"workspace-{user_id}"
    
    env = {
        "PASSWORD": kwargs.get("password", f"student{user_id}"),
        "WORKSPACE_NAME": workspace_name,
        "USER_ID": str(user_id),
    }
    env.update(kwargs.get("env", {}))
    
    params = JobParams(
        name=f"codeserver-{user_id}",
        image=kwargs.get("image", "codercom/code-server:latest"),
        ports=kwargs.get("ports", [8080]),
        env=env,
        user_id=user_id,
        cpu_limit=kwargs.get("cpu_limit"),
        memory_limit=kwargs.get("memory_limit"),
        storage_size=kwargs.get("storage_size"),
    )
    
    return params

from base.logger import logger
LOGGER = logger(__spec__, __file__)


from test import AsyncTestCase, RUNNER, setup_test, guard_once

# 测试用集群实例
_TEST_CLUSTER = None
_KUBERNETES_CLUSTER = None


def setUpModule():
    """模块级设置"""
    try:
        setup_test(__name__)
    except Exception as e:
        print(f"Warning: Module setup failed: {e}")


@guard_once
async def ainit_kubernetes_cluster():
    """初始化 Kubernetes 测试集群"""
    global _KUBERNETES_CLUSTER
    
    try:
        LOGGER.info("🔧 Initializing Kubernetes test cluster...")
        LOGGER.info("🎭 Creating enhanced mock cluster for Kubernetes testing...")
        try:
            from cluster.mock import MockCluster
            from cluster import ClusterConfig
            
            config = ClusterConfig()
            _KUBERNETES_CLUSTER = MockCluster(config)
            _KUBERNETES_CLUSTER._is_mock = True
            _KUBERNETES_CLUSTER._cluster_type = "kubernetes"
            await _KUBERNETES_CLUSTER.initialize()
            
            LOGGER.info("✅ Enhanced mock Kubernetes cluster initialized for testing")
            return _KUBERNETES_CLUSTER
        except ImportError:
            LOGGER.error("❌ Could not import mock cluster")
            return None
        
    except Exception as e:
        LOGGER.error(f"💥 Failed to initialize any Kubernetes cluster: {e}")
        LOGGER.error(f"Traceback: {traceback.format_exc()}")
        return None


@guard_once
async def ainit_test_cluster():
    """初始化测试用集群"""
    global _TEST_CLUSTER
    
    try:
        LOGGER.info("🔧 Initializing test cluster...")
        
        # 创建 Mock 集群用于基础测试
        _TEST_CLUSTER = create(type="mock")
        await _TEST_CLUSTER.initialize()
        
        LOGGER.info(f"✅ Test cluster initialized: {_TEST_CLUSTER.__class__.__name__}")
        return _TEST_CLUSTER
        
    except Exception as e:
        LOGGER.error(f"💥 Failed to initialize test cluster: {e}")
        LOGGER.error(f"Traceback: {traceback.format_exc()}")
        return None


def ensure_kubernetes_cluster():
    """确保 Kubernetes 集群已初始化"""
    global _KUBERNETES_CLUSTER
    
    if _KUBERNETES_CLUSTER is None:
        LOGGER.info("🔄 Kubernetes cluster not initialized, initializing now...")
        try:
            _KUBERNETES_CLUSTER = RUNNER.run(ainit_kubernetes_cluster())
        except Exception as e:
            LOGGER.error(f"💥 Failed to initialize Kubernetes cluster: {e}")
            _KUBERNETES_CLUSTER = None
    
    return _KUBERNETES_CLUSTER


def get_kubernetes_cluster():
    """获取 Kubernetes 测试集群实例"""
    return ensure_kubernetes_cluster()


def get_test_cluster():
    """获取测试集群实例"""
    global _TEST_CLUSTER
    
    if _TEST_CLUSTER is None:
        LOGGER.info("🔄 Test cluster not initialized, initializing now...")
        try:
            _TEST_CLUSTER = RUNNER.run(ainit_test_cluster())
        except Exception as e:
            LOGGER.error(f"💥 Failed to initialize test cluster: {e}")
            _TEST_CLUSTER = None
    
    return _TEST_CLUSTER


class ClusterTestBase(AsyncTestCase):
    """集群测试基类"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_jobs = []
    
    def setUp(self):
        """测试方法设置"""
        super().setUp()
        self.created_jobs = []
        self.cluster = get_test_cluster()
        
        if self.cluster is None:
            LOGGER.warning("⚠️  Test cluster is None, creating temporary cluster")
            try:
                temp_cluster = create(type="mock")
                RUNNER.run(temp_cluster.initialize())
                self.cluster = temp_cluster
                global _TEST_CLUSTER
                _TEST_CLUSTER = temp_cluster
                LOGGER.info("✅ Temporary test cluster created")
            except Exception as e:
                LOGGER.error(f"💥 Failed to create temporary cluster: {e}")
        
        self.assertIsNotNone(self.cluster, "Test cluster should be available")
    
    def tearDown(self):
        """测试方法清理"""
        if self.cluster and self.created_jobs:
            async def cleanup_jobs():
                for job_id in self.created_jobs:
                    try:
                        await self.cluster.cleanup(job_id)
                        LOGGER.debug(f"🧹 Cleaned up job: {job_id}")
                    except Exception as e:
                        LOGGER.warning(f"⚠️  Failed to cleanup job {job_id}: {e}")
            
            try:
                RUNNER.run(cleanup_jobs())
            except Exception as e:
                LOGGER.warning(f"⚠️  Job cleanup error: {e}")
            
            self.created_jobs.clear()
        
        super().tearDown()
    
    def track_job(self, job_id: str):
        """跟踪创建的作业，用于自动清理"""
        self.created_jobs.append(job_id)
        LOGGER.debug(f"📝 Tracking job for cleanup: {job_id}")
    
    def create_test_job_params(self, name: str = "test-job", **kwargs) -> JobParams:
        """创建测试用的作业参数"""
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
        self.assertIsNotNone(job_info.user_id)
    
    def assert_code_server_job_valid(self, job_info):
        """验证 code-server 作业的特殊要求"""
        self.assert_job_info_valid(job_info)
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
