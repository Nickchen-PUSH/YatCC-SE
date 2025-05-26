"""Mock 集群测试

测试 Mock 集群的用户独立 code-server 功能。
"""

from cluster import JobInfo, ClusterError, JobNotFoundError
from base.logger import logger
from . import ClusterTestBase, RUNNER

LOGGER = logger(__spec__, __file__)


class MockClusterTest(ClusterTestBase):
    """Mock 集群功能测试"""
    
    def test_submit_user_code_server_job(self):
        """测试提交用户 code-server 作业"""
        async def _test():
            user_id = 5001
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="test-workspace"
            )
            
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            # 验证作业信息
            self.assert_code_server_job_valid(job_info)
            self.assert_user_isolation(job_info, user_id)
            self.assertIsNotNone(job_info.service_url)
            
            LOGGER.info(f"Mock user {user_id} code-server job submitted: {job_info.id}")
        
        RUNNER.run(_test())
    
    def test_multiple_users_mock_deployments(self):
        """测试多用户模拟部署"""
        async def _test():
            user_ids = [5001, 5002, 5003]
            jobs = []
            
            for user_id in user_ids:
                job_params = self.create_code_server_params(user_id=user_id)
                job_info = await self.cluster.submit_job(job_params)
                jobs.append(job_info)
                self.track_job(job_info.id)
                
                self.assert_user_isolation(job_info, user_id)
            
            # 验证所有用户都有独立实例
            job_ids = [job.id for job in jobs]
            self.assertEqual(len(job_ids), len(set(job_ids)))
            
            LOGGER.info(f"Mock multiple users: {len(jobs)} instances")
        
        RUNNER.run(_test())
    
    def test_user_job_list(self):
        """测试用户作业列表"""
        async def _test():
            user1_id = 5010
            user2_id = 5011
            
            # 创建两个用户的作业
            job1_params = self.create_code_server_params(user_id=user1_id)
            job2_params = self.create_code_server_params(user_id=user2_id)
            
            job1_info = await self.cluster.submit_job(job1_params)
            job2_info = await self.cluster.submit_job(job2_params)
            
            self.track_job(job1_info.id)
            self.track_job(job2_info.id)
            
            # 验证用户存在于作业列表中
            jobs = await self.cluster.list_jobs()
            self.assertIn(job1_info, jobs)
            self.assertIn(job2_info, jobs)
            
            LOGGER.info("Mock user job list verified")
        
        RUNNER.run(_test())


if __name__ == "__main__":
    import unittest
    unittest.main()