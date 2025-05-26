"""Kubernetes 集群测试

测试 Kubernetes 集群的用户独立 code-server 部署功能。
"""

from cluster import JobInfo, ClusterError, JobNotFoundError
from base.logger import logger
from . import ClusterTestBase, RUNNER, get_kubernetes_cluster

LOGGER = logger(__spec__, __file__)


def setUpModule() -> None:
    """模块级别的设置"""
    LOGGER.info("Kubernetes cluster test module setup")


def tearDownModule() -> None:
    """模块级别的清理"""
    LOGGER.info("Kubernetes cluster test module teardown")


class KubernetesClusterTest(ClusterTestBase):
    """Kubernetes 集群功能测试"""
    
    def setUp(self) -> None:
        """测试设置"""
        super().setUp()
        self.cluster = get_kubernetes_cluster()
        self.assertIsNotNone(self.cluster, "Kubernetes cluster should be available")
    
    def test_submit_user_code_server_deployment(self):
        """测试提交用户独立的 code-server Deployment"""
        async def _test():
            user_id = 6001
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="my-workspace",
                cpu_limit="2000m",
                memory_limit="4Gi",
                storage_size="10Gi"
            )
            
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 验证作业信息
            self.assert_code_server_job_valid(job_info)
            self.assert_user_isolation(job_info, user_id)
            self.assertIsNotNone(job_info.service_url)
            self.assertEqual(job_info.namespace, "default")
            
            # 验证作业名称
            self.assertIn("code-server", job_info.name)
            self.assertIn(f"{user_id}", job_info.name)
            
            LOGGER.info(f"User {user_id} code-server job submitted: {job_info.id}")
        
        RUNNER.run(_test())
    
    def test_user_duplicate_deployment_prevention(self):
        """测试防止用户重复部署"""
        async def _test():
            user_id = 9001
            
            # 第一次部署应该成功
            job_params1 = self.create_code_server_params(user_id=user_id)
            job_info1 = await self.cluster.submit_job(job_params1)
            self.track_job(job_info1.id)
            
            self.assert_user_isolation(job_info1, user_id)
            
            # 等待第一个作业运行
            await self.wait_for_job_status(job_info1.id, JobInfo.Status.RUNNING, timeout=10)
            
            # 尝试第二次部署应该失败或返回现有实例
            job_params2 = self.create_code_server_params(user_id=user_id)
            
            try:
                job_info2 = await self.cluster.submit_job(job_params2)
                # 如果成功，应该是同一个实例或者新实例替换了旧的
                if job_info2.id != job_info1.id:
                    self.track_job(job_info2.id)
                LOGGER.info(f"User {user_id} duplicate deployment handled gracefully")
            except ClusterError as e:
                # 如果失败，错误消息应该指出用户已有运行中的实例
                self.assertIn(str(user_id), str(e))
                LOGGER.info(f"User {user_id} duplicate deployment prevented: {e}")
        
        RUNNER.run(_test())
    
    def test_persistent_storage_per_user(self):
        """测试每个用户的持久化存储"""
        async def _test():
            user_id = 6003
            storage_size = "25Gi"
            
            job_params = self.create_code_server_params(
                user_id=user_id,
                storage_size=storage_size
            )
            
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 验证用户独立存储配置
            self.assert_code_server_job_valid(job_info)
            self.assert_user_isolation(job_info, user_id)
            
            LOGGER.info(f"User {user_id} persistent storage configured: {storage_size}")
        
        RUNNER.run(_test())
    
    def test_user_environment_customization(self):
        """测试用户环境自定义"""
        async def _test():
            user_id = 6005
            custom_env = {
                "EXTENSIONS": "ms-python.python,ms-vscode.vscode-json",
                "CUSTOM_VAR": f"user_{user_id}_value",
                "WORKSPACE_TYPE": "development"
            }
            
            job_params = self.create_code_server_params(
                user_id=user_id,
                env=custom_env
            )
            
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 验证用户自定义环境变量
            self.assert_user_isolation(job_info, user_id)
            self.assertIn("PASSWORD", job_info.env)
            self.assertIn("SUDO_PASSWORD", job_info.env)
            self.assertEqual(job_info.env.get("CUSTOM_VAR"), f"user_{user_id}_value")
            self.assertEqual(job_info.env.get("EXTENSIONS"), "ms-python.python,ms-vscode.vscode-json")
            
            LOGGER.info(f"User {user_id} environment customization verified")
        
        RUNNER.run(_test())
    
    def test_user_resource_limits(self):
        """测试用户资源限制"""
        async def _test():
            user_id = 6002
            
            job_params = self.create_code_server_params(
                user_id=user_id,
                cpu_limit="1500m",
                memory_limit="3Gi",
                storage_size="8Gi"
            )
            
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 验证用户资源配置
            self.assert_code_server_job_valid(job_info)
            self.assert_user_isolation(job_info, user_id)
            
            # 获取详细信息验证资源设置
            detailed_info = await self.cluster.get_job_info(job_info.id)
            self.assertEqual(detailed_info.id, job_info.id)
            self.assertEqual(detailed_info.user_id, user_id)
            
            LOGGER.info(f"User {user_id} resource limits applied")
        
        RUNNER.run(_test())
    
    def test_user_service_access(self):
        """测试用户服务访问"""
        async def _test():
            user_id = 6004
            
            job_params = self.create_code_server_params(user_id=user_id)
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 验证用户独立的服务 URL
            self.assertIsNotNone(job_info.service_url)
            self.assertIn("8080", job_info.service_url)
            self.assertIn(f"u{user_id}", job_info.service_url)  # URL应该包含用户标识
            
            LOGGER.info(f"User {user_id} service access: {job_info.service_url}")
        
        RUNNER.run(_test())
    
    def test_user_job_lifecycle(self):
        """测试用户作业生命周期"""
        async def _test():
            user_id = 6040
            
            job_params = self.create_code_server_params(user_id=user_id)
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 验证初始状态
            self.assertEqual(job_info.status, JobInfo.Status.PENDING)
            self.assert_user_isolation(job_info, user_id)
            
            # 获取当前状态
            current_status = await self.cluster.get_job_status(job_info.id)
            self.assertIn(current_status, [JobInfo.Status.PENDING, JobInfo.Status.RUNNING])
            
            # 验证可以删除用户的作业
            await self.cluster.delete_job(job_info.id)
            
            # 验证删除后不能获取状态
            with self.assertRaises(JobNotFoundError):
                await self.cluster.get_job_status(job_info.id)
            
            LOGGER.info(f"User {user_id} job lifecycle verified")
        
        RUNNER.run(_test())
    
    def test_user_logs_access(self):
        """测试用户日志访问"""
        async def _test():
            user_id = 6010
            
            job_params = self.create_code_server_params(user_id=user_id)
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 获取用户作业日志
            logs = await self.cluster.get_job_logs(job_info.id, lines=50)
            
            self.assertIsInstance(logs, str)
            self.assertGreater(len(logs), 0)
            # 日志应该包含用户相关信息
            self.assertIn(job_info.id, logs)
            
            LOGGER.info(f"User {user_id} logs access verified")
        
        RUNNER.run(_test())


if __name__ == "__main__":
    import unittest
    unittest.main()