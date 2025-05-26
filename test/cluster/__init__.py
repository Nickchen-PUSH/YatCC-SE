"""cluster 模块测试包

提供 cluster 模块的完整测试覆盖，专注于用户独立的 code-server 部署。
"""

import asyncio as aio
import sys
import traceback
import time
from cluster import create, JobParams, create_code_server_job, JobInfo
from base.logger import logger
from .. import AsyncTestCase, RUNNER, setup_test, guard_once

LOGGER = logger(__spec__, __file__)

# 测试用集群实例
_TEST_CLUSTER = None
_KUBERNETES_CLUSTER = None


async def check_kubernetes_availability():
    """检查 Kubernetes 可用性"""
    try:
        LOGGER.info("Checking Kubernetes availability...")
        
        # 首先尝试直接的 kubectl
        result = await aio.create_subprocess_exec(
            'kubectl', 'version', '--client',
            stdout=aio.subprocess.PIPE,
            stderr=aio.subprocess.PIPE
        )
        await result.wait()
        
        if result.returncode != 0:
            # 尝试 minikube kubectl
            LOGGER.info("Direct kubectl not available, trying minikube kubectl...")
            result = await aio.create_subprocess_exec(
                'minikube', 'kubectl', '--', 'version', '--client',
                stdout=aio.subprocess.PIPE,
                stderr=aio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode != 0:
                LOGGER.warning("Neither kubectl nor minikube kubectl available")
                return False
            else:
                # 使用 minikube kubectl 进行后续检查
                kubectl_cmd = ['minikube', 'kubectl', '--']
        else:
            # 使用直接的 kubectl
            kubectl_cmd = ['kubectl']
        
        LOGGER.info("✅ kubectl is available")
        
        # 检查集群连接
        result = await aio.create_subprocess_exec(
            *(kubectl_cmd + ['cluster-info', '--request-timeout=5s']),
            stdout=aio.subprocess.PIPE,
            stderr=aio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0:
            cluster_info = stdout.decode().strip()
            LOGGER.info(f"✅ Kubernetes cluster is available")
            LOGGER.info(f"Cluster info: {cluster_info}")
            
            # 测试是否能创建资源
            result = await aio.create_subprocess_exec(
                *(kubectl_cmd + ['auth', 'can-i', 'create', 'deployments']),
                stdout=aio.subprocess.PIPE,
                stderr=aio.subprocess.PIPE
            )
            await result.wait()
            
            if result.returncode == 0:
                LOGGER.info("✅ Can create deployments")
                return True
            else:
                LOGGER.warning("⚠️  Cannot create deployments, using mock cluster")
                return False
        else:
            error_msg = stderr.decode().strip()
            LOGGER.warning(f"❌ No Kubernetes cluster connection. Error: {error_msg}")
            return False
            
    except Exception as e:
        LOGGER.warning(f"Kubernetes availability check failed: {e}")
        return False


@guard_once
async def ainit_kubernetes_cluster():
    """初始化 Kubernetes 测试集群"""
    global _KUBERNETES_CLUSTER
    
    try:
        LOGGER.info("🔧 Initializing Kubernetes test cluster...")
        
        # 检查 Kubernetes 可用性
        k8s_available = await check_kubernetes_availability()
        
        if k8s_available:
            try:
                # 尝试创建真实的 Kubernetes 集群连接
                LOGGER.info("🚀 Attempting to create real Kubernetes cluster connection...")
                _KUBERNETES_CLUSTER = create(type="kubernetes")
                await _KUBERNETES_CLUSTER.initialize()
                _KUBERNETES_CLUSTER._is_mock = False
                LOGGER.info(f"✅ Real Kubernetes cluster initialized: {_KUBERNETES_CLUSTER.__class__.__name__}")
                
                # 验证能够列出命名空间（使用 asyncio.to_thread）
                try:
                    namespaces = await aio.to_thread(_KUBERNETES_CLUSTER.core_v1.list_namespace)
                    namespace_names = [ns.metadata.name for ns in namespaces.items[:3]]
                    LOGGER.info(f"📋 Available namespaces: {namespace_names}...")
                    
                    # 验证能够列出节点
                    nodes = await aio.to_thread(_KUBERNETES_CLUSTER.core_v1.list_node)
                    node_names = [node.metadata.name for node in nodes.items[:2]]
                    LOGGER.info(f"🖥️  Available nodes: {node_names}...")
                    
                    return _KUBERNETES_CLUSTER
                    
                except Exception as verify_error:
                    LOGGER.warning(f"⚠️  Kubernetes cluster verification failed: {verify_error}")
                    # 即使验证失败，仍然返回集群对象，因为初始化成功了
                    return _KUBERNETES_CLUSTER
                
            except Exception as k8s_error:
                LOGGER.warning(f"❌ Failed to initialize real Kubernetes: {k8s_error}")
                LOGGER.warning(f"Error details: {traceback.format_exc()}")
        else:
            LOGGER.warning("⚠️  Kubernetes not available, will use enhanced mock cluster")
        
        # 回退到增强型 Mock 集群
        LOGGER.info("🎭 Creating enhanced mock cluster for Kubernetes testing...")
        from cluster.mock import MockCluster
        from cluster import ClusterConfig
        
        config = ClusterConfig()
        _KUBERNETES_CLUSTER = MockCluster(config)
        _KUBERNETES_CLUSTER._is_mock = True
        _KUBERNETES_CLUSTER._cluster_type = "kubernetes"
        await _KUBERNETES_CLUSTER.initialize()
        
        LOGGER.info("✅ Enhanced mock Kubernetes cluster initialized for testing")
        return _KUBERNETES_CLUSTER
        
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
    
    def tearDown(self) -> None:
        """测试方法清理"""
        if self.cluster and self.created_jobs:
            async def cleanup_jobs():
                for job_id in self.created_jobs:
                    try:
                        await self.cluster.delete_job(job_id)
                        LOGGER.debug(f"🧹 Cleaned up job: {job_id}")
                    except Exception as e:
                        LOGGER.warning(f"⚠️  Failed to cleanup job {job_id}: {e}")
            
            try:
                RUNNER.run(cleanup_jobs())
            except Exception as e:
                LOGGER.warning(f"⚠️  Job cleanup error: {e}")
            
            self.created_jobs.clear()
    
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
        # 验证用户独立部署的必须字段
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
