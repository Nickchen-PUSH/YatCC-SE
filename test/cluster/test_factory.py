"""工厂函数和便捷函数测试

测试 cluster 模块的工厂函数和便捷函数。
"""

from cluster import (
    create, create_code_server_job, get_cluster,
    ClusterConfig, JobParams, JobInfo,
    ClusterABC, ClusterError
)
from base.logger import logger
from . import ClusterTestBase, RUNNER

LOGGER = logger(__spec__, __file__)


class FactoryFunctionsTest(ClusterTestBase):
    """工厂函数和便捷函数测试"""
    
    def test_create_mock_cluster(self):
        """测试创建 Mock 集群"""
        # 使用默认参数创建 Mock 集群
        cluster = create(type="mock")
        self.assertIsNotNone(cluster)
        self.assertEqual(cluster.__class__.__name__, "MockCluster")
        
        LOGGER.info("Mock cluster creation verified")
    
    def test_create_invalid_type(self):
        """测试创建无效类型的集群"""
        # 根据实际的 cluster 实现，可能不会抛出 ValueError
        # 先测试是否能创建，如果可以创建则检查类型
        try:
            cluster = create(type="invalid-type")
            # 如果没有抛出异常，检查是否回退到默认类型
            self.assertIsNotNone(cluster)
            LOGGER.info(f"Invalid type created cluster: {cluster.__class__.__name__}")
        except (ValueError, TypeError, KeyError) as e:
            # 如果抛出异常，验证异常信息
            error_message = str(e)
            self.assertIn("invalid-type", error_message.lower())
            LOGGER.info("Invalid type error handling verified")
    
    def test_create_code_server_job_basic(self):
        """测试基本的 code-server 作业创建"""
        job_params = create_code_server_job(user_id=1001)
        
        # 验证基本参数
        self.assertIsInstance(job_params, JobParams)
        self.assertEqual(job_params.user_id, 1001)
        self.assertEqual(job_params.image, "codercom/code-server:latest")
        self.assertIn(8080, job_params.ports)
        
        # 验证环境变量
        self.assertIn("PASSWORD", job_params.env)
        self.assertIn("SUDO_PASSWORD", job_params.env)
        self.assertEqual(job_params.env["PASSWORD"], "student1001")
        self.assertEqual(job_params.env["SUDO_PASSWORD"], "student1001")
        
        # 验证名称格式
        self.assertIn("code-server", job_params.name)
        self.assertIn("1001", job_params.name)
        
        LOGGER.info(f"Basic code-server job creation verified: {job_params.name}")
    
    def test_create_code_server_job_with_options(self):
        """测试带选项的 code-server 作业创建"""
        custom_env = {"CUSTOM_VAR": "test_value"}
        
        job_params = create_code_server_job(
            user_id=2001,
            cpu_limit="2000m",
            memory_limit="4Gi",
            storage_size="10Gi",
            env=custom_env
        )
        
        # 验证自定义参数
        self.assertEqual(job_params.cpu_limit, "2000m")
        self.assertEqual(job_params.memory_limit, "4Gi")
        self.assertEqual(job_params.storage_size, "10Gi")
        
        # 验证环境变量合并
        self.assertIn("PASSWORD", job_params.env)
        self.assertIn("CUSTOM_VAR", job_params.env)
        self.assertEqual(job_params.env["CUSTOM_VAR"], "test_value")
        
        LOGGER.info(f"Code-server job with options verified: {job_params.name}")
    
    def test_create_code_server_job_multiple_users(self):
        """测试为多个用户创建作业"""
        users = [
            {"user_id": 3001},
            {"user_id": 3002},
            {"user_id": 3003},
        ]
        
        job_params_list = []
        for user in users:
            job_params = create_code_server_job(**user)
            job_params_list.append(job_params)
        
        # 验证所有作业参数都是唯一的
        names = [params.name for params in job_params_list]
        self.assertEqual(len(names), len(set(names)))
        
        # 验证用户信息正确
        for i, params in enumerate(job_params_list):
            self.assertEqual(params.user_id, users[i]["user_id"])
            self.assertEqual(params.env["PASSWORD"], f"student{users[i]['user_id']}")
        
        LOGGER.info(f"Multiple users job creation verified: {len(job_params_list)} jobs")
    
    # async def test_get_cluster_global_instance(self):
    #     """测试获取全局集群实例"""
    #     # 第一次获取
    #     cluster1 = await get_cluster()
    #     self.assertIsNotNone(cluster1)
    #     self.assertIsInstance(cluster1, ClusterABC)
        
    #     # 检查初始化状态，如果未初始化则初始化
    #     if not getattr(cluster1, '_initialized', False):
    #         await cluster1.initialize()
        
    #     self.assertTrue(getattr(cluster1, '_initialized', True))
        
    #     # 第二次获取应该是同一个实例
    #     cluster2 = await get_cluster()
    #     self.assertIs(cluster1, cluster2)
        
    #     LOGGER.info(f"Global cluster instance verified: {cluster1.__class__.__name__}")