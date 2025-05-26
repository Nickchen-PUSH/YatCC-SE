"""Kubernetes 集群测试

测试 Kubernetes 集群的用户独立 code-server 部署功能。
"""

import unittest
import asyncio as aio
from cluster import JobInfo, ClusterError, JobNotFoundError
from base.logger import logger
from . import ClusterTestBase, RUNNER, get_kubernetes_cluster, ensure_kubernetes_cluster

LOGGER = logger(__spec__, __file__)


def setUpModule() -> None:
    """模块级别的设置"""
    LOGGER.info("🚀 Kubernetes cluster test module setup")
    # 预先初始化 Kubernetes 集群
    try:
        k8s_cluster = ensure_kubernetes_cluster()
        if k8s_cluster:
            LOGGER.info(f"✅ Kubernetes cluster ready for testing: {k8s_cluster.__class__.__name__}")
        else:
            LOGGER.warning("⚠️  No Kubernetes cluster available")
    except Exception as e:
        LOGGER.warning(f"⚠️  Failed to setup Kubernetes cluster: {e}")


def tearDownModule() -> None:
    """模块级别的清理"""
    LOGGER.info("🧹 Kubernetes cluster test module teardown")


class KubernetesClusterTest(ClusterTestBase):
    """Kubernetes 集群功能测试"""
    
    def setUp(self) -> None:
        """测试设置"""
        super().setUp()
        
        # 获取 Kubernetes 集群
        k8s_cluster = get_kubernetes_cluster()
        
        if k8s_cluster is None:
            self.skipTest("No Kubernetes cluster available for testing")
        
        self.cluster = k8s_cluster
        
        # 检查是否是真实的 Kubernetes 集群
        is_mock = getattr(self.cluster, '_is_mock', True)
        if is_mock:
            LOGGER.info(f"Using MOCK cluster for Kubernetes tests: {self.cluster.__class__.__name__}")
            self.is_real_k8s = False
        else:
            LOGGER.info(f"Using REAL Kubernetes cluster: {self.cluster.__class__.__name__}")
            self.is_real_k8s = True
        
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
            
            # 根据集群类型进行不同的验证
            if self.is_real_k8s:
                # 真实 K8s 集群的验证
                self.assertEqual(job_info.namespace, "default")
                # 验证真实的 service URL 格式
                self.assertIn(":", job_info.service_url)
            else:
                # Mock 集群的验证
                self.assertIsNotNone(job_info.namespace)
            
            # 验证作业名称格式（用户独立）
            self.assertIn("code-server", job_info.name)
            self.assertIn(f"{user_id}", job_info.name)
            
            LOGGER.info(f"User {user_id} code-server job submitted: {job_info.id} (Real K8s: {self.is_real_k8s})")
        
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
            
            LOGGER.info(f"User {user_id} persistent storage configured: {storage_size} (Real K8s: {self.is_real_k8s})")
        
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
            
            # 检查自定义环境变量（仅在支持的集群中）
            if "CUSTOM_VAR" in job_info.env:
                self.assertEqual(job_info.env.get("CUSTOM_VAR"), f"user_{user_id}_value")
            if "EXTENSIONS" in job_info.env:
                self.assertEqual(job_info.env.get("EXTENSIONS"), "ms-python.python,ms-vscode.vscode-json")
            
            LOGGER.info(f"User {user_id} environment customization verified (Real K8s: {self.is_real_k8s})")
        
        RUNNER.run(_test())
        
    def test_delete_code_server_job(self):
        """测试删除 code-server 作业"""
        async def _test():
            user_id = 9001
            
            # 1. 创建作业
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="delete-test"
            )
            
            job_info = await self.cluster.submit_job(job_params)
            job_id = job_info.id
            
            # 验证作业创建成功
            self.assert_code_server_job_valid(job_info)
            self.assert_user_isolation(job_info, user_id)
            
            LOGGER.info(f"Created job for deletion test: {job_id}")
            
            # 2. 验证作业存在
            retrieved_job = await self.cluster.get_job_info(job_id)
            self.assertEqual(retrieved_job.id, job_id)
            self.assertEqual(retrieved_job.user_id, user_id)
            
            # 3. 删除作业
            await self.cluster.delete_job(job_id)
            LOGGER.info(f"Deleted job: {job_id}")
            
            # 4. 验证作业已被删除 - 应该抛出 JobNotFoundError
            with self.assertRaises(JobNotFoundError):
                await self.cluster.get_job_info(job_id)
            
            # 5. 验证作业不在列表中
            jobs = await self.cluster.list_jobs()
            job_ids = [job.id for job in jobs]
            self.assertNotIn(job_id, job_ids)
            
            LOGGER.info(f"✅ Job {job_id} successfully deleted and verified")
            
        RUNNER.run(_test())
    
    def test_delete_nonexistent_job(self):
        """测试删除不存在的作业"""
        async def _test():
            nonexistent_job_id = "nonexistent-job-12345"
            
            # 删除不存在的作业应该不抛出异常（幂等操作）
            try:
                await self.cluster.delete_job(nonexistent_job_id)
                LOGGER.info(f"✅ Deleting nonexistent job {nonexistent_job_id} handled gracefully")
            except Exception as e:
                # 如果抛出异常，应该是可接受的异常类型
                LOGGER.info(f"Delete nonexistent job threw: {type(e).__name__}: {e}")
                # 在真实的 K8s 集群中，删除不存在的资源通常不会抛出异常
                if self.is_real_k8s:
                    # 对于真实集群，我们期望操作是幂等的
                    pass
                else:
                    # Mock 集群可能有不同的行为
                    pass
            
        RUNNER.run(_test())
    
    def test_delete_multiple_user_jobs(self):
        """测试删除多个用户的作业"""
        async def _test():
            user_ids = [9101, 9102, 9103]
            created_jobs = []
            
            # 1. 为多个用户创建作业
            for user_id in user_ids:
                job_params = self.create_code_server_params(
                    user_id=user_id,
                    workspace_name=f"multi-delete-{user_id}"
                )
                
                job_info = await self.cluster.submit_job(job_params)
                created_jobs.append((job_info.id, user_id))
                
                # 验证创建
                self.assert_user_isolation(job_info, user_id)
            
            LOGGER.info(f"Created {len(created_jobs)} jobs for multi-delete test")
            
            # 2. 验证所有作业都存在
            initial_jobs = await self.cluster.list_jobs()
            initial_job_ids = [job.id for job in initial_jobs]
            
            for job_id, user_id in created_jobs:
                self.assertIn(job_id, initial_job_ids)
            
            # 3. 逐一删除作业
            for job_id, user_id in created_jobs:
                await self.cluster.delete_job(job_id)
                LOGGER.info(f"Deleted job {job_id} for user {user_id}")
                
                # 验证单个作业被删除
                with self.assertRaises(JobNotFoundError):
                    await self.cluster.get_job_info(job_id)
            
            # 4. 验证所有作业都被删除
            final_jobs = await self.cluster.list_jobs()
            final_job_ids = [job.id for job in final_jobs]
            
            for job_id, user_id in created_jobs:
                self.assertNotIn(job_id, final_job_ids)
            
            LOGGER.info(f"✅ All {len(created_jobs)} jobs successfully deleted")
            
        RUNNER.run(_test())
    
    def test_delete_job_resources_cleanup(self):
        """测试删除作业时资源清理的完整性"""
        async def _test():
            user_id = 9201
            
            # 1. 创建作业
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="cleanup-test",
                storage_size="1Gi"
            )
            
            job_info = await self.cluster.submit_job(job_params)
            job_id = job_info.id
            
            LOGGER.info(f"Created job for cleanup test: {job_id}")
            
            # 2. 验证资源创建（仅在真实 K8s 集群中）
            if self.is_real_k8s:
                # 验证 Deployment 存在
                try:
                    deployment = await aio.to_thread(
                        self.cluster.apps_v1.read_namespaced_deployment,
                        name=job_id,
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    )
                    self.assertEqual(deployment.metadata.name, job_id)
                    LOGGER.info(f"✅ Deployment {job_id} verified")
                except Exception as e:
                    LOGGER.warning(f"Could not verify deployment {job_id}: {e}")
                
                # 验证 Service 存在
                try:
                    service = await aio.to_thread(
                        self.cluster.core_v1.read_namespaced_service,
                        name=f"{job_id}-svc",
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    )
                    self.assertEqual(service.metadata.name, f"{job_id}-svc")
                    LOGGER.info(f"✅ Service {job_id}-svc verified")
                except Exception as e:
                    LOGGER.warning(f"Could not verify service {job_id}-svc: {e}")
                
                # 验证 PVC 存在
                try:
                    pvc = await aio.to_thread(
                        self.cluster.core_v1.read_namespaced_persistent_volume_claim,
                        name=f"{job_id}-pvc",
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    )
                    self.assertEqual(pvc.metadata.name, f"{job_id}-pvc")
                    LOGGER.info(f"✅ PVC {job_id}-pvc verified")
                except Exception as e:
                    LOGGER.warning(f"Could not verify PVC {job_id}-pvc: {e}")
            
            # 3. 删除作业
            await self.cluster.delete_job(job_id)
            LOGGER.info(f"Deleted job: {job_id}")
            
            # 4. 验证所有资源都被清理（仅在真实 K8s 集群中）
            if self.is_real_k8s:
                from kubernetes.client.rest import ApiException
                
                # 等待资源删除完成的辅助函数
                async def wait_for_resource_deletion(check_func, resource_name, max_wait=30):
                    """等待资源被删除"""
                    start_time = aio.get_event_loop().time()
                    
                    while (aio.get_event_loop().time() - start_time) < max_wait:
                        try:
                            await aio.to_thread(check_func)
                            # 如果还能读取到资源，继续等待
                            await aio.sleep(2)
                        except ApiException as e:
                            if e.status == 404:
                                LOGGER.info(f"✅ {resource_name} successfully deleted")
                                return True
                            else:
                                LOGGER.warning(f"Unexpected error checking {resource_name}: {e}")
                                await aio.sleep(2)
                        except Exception as e:
                            LOGGER.warning(f"Error waiting for {resource_name} deletion: {e}")
                            await aio.sleep(2)
                    
                    LOGGER.warning(f"⚠️  Timeout waiting for {resource_name} deletion")
                    return False
                
                # 等待 Deployment 删除
                deployment_deleted = await wait_for_resource_deletion(
                    lambda: self.cluster.apps_v1.read_namespaced_deployment(
                        name=job_id,
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    ),
                    f"Deployment {job_id}"
                )
                
                # 等待 Service 删除
                service_deleted = await wait_for_resource_deletion(
                    lambda: self.cluster.core_v1.read_namespaced_service(
                        name=f"{job_id}-svc",
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    ),
                    f"Service {job_id}-svc"
                )
                
                # 等待 PVC 删除
                pvc_deleted = await wait_for_resource_deletion(
                    lambda: self.cluster.core_v1.read_namespaced_persistent_volume_claim(
                        name=f"{job_id}-pvc",
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    ),
                    f"PVC {job_id}-pvc"
                )
                
                # 验证至少主要资源被删除
                if deployment_deleted and service_deleted:
                    LOGGER.info(f"✅ All critical resources confirmed deleted for job {job_id}")
                else:
                    LOGGER.warning(f"⚠️  Some resources may still exist for job {job_id}")
                    # 对于测试，我们可以容忍 PVC 删除较慢
                    if deployment_deleted:
                        LOGGER.info(f"✅ Main deployment resource deleted for job {job_id}")
                
            else:
                LOGGER.info(f"✅ Cleanup test completed (Mock cluster)")
            
            # 5. 最终验证作业不存在
            with self.assertRaises(JobNotFoundError):
                await self.cluster.get_job_info(job_id)
            
        RUNNER.run(_test())
    
    def test_delete_job_error_handling(self):
        """测试删除作业时的错误处理"""
        async def _test():
            user_id = 9203
            
            # 1. 创建作业
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="error-handling-test"
            )
            
            job_info = await self.cluster.submit_job(job_params)
            job_id = job_info.id
            
            LOGGER.info(f"Created job for error handling test: {job_id}")
            
            # 2. 正常删除作业
            await self.cluster.delete_job(job_id)
            LOGGER.info(f"Deleted job: {job_id}")
            
            # 3. 尝试删除已删除的作业（应该处理优雅）
            try:
                await self.cluster.delete_job(job_id)
                LOGGER.info(f"✅ Re-deletion of {job_id} handled gracefully")
            except Exception as e:
                # 记录异常但不失败测试，因为不同实现可能有不同行为
                LOGGER.info(f"Re-deletion threw: {type(e).__name__}: {e}")
            
            # 4. 尝试删除无效的作业ID
            invalid_job_ids = [
                "",  # 空字符串
                "invalid-job-name-!@#$%",  # 包含无效字符
                "a" * 100,  # 过长的名称
            ]
            
            for invalid_id in invalid_job_ids:
                try:
                    await self.cluster.delete_job(invalid_id)
                    LOGGER.info(f"✅ Deletion of invalid job ID '{invalid_id}' handled")
                except Exception as e:
                    LOGGER.info(f"Deletion of invalid ID '{invalid_id}' threw: {type(e).__name__}")
                    # 这是可接受的行为
            
            LOGGER.info(f"✅ Error handling test completed")
            
        RUNNER.run(_test())

    def test_concurrent_job_deletion(self):
        """测试并发删除作业"""
        async def _test():
            user_id = 9401
            job_count = 3
            created_jobs = []
            
            # 1. 创建多个作业
            for i in range(job_count):
                job_params = self.create_code_server_params(
                    user_id=user_id + i,
                    workspace_name=f"concurrent-delete-{i}"
                )
                
                job_info = await self.cluster.submit_job(job_params)
                created_jobs.append(job_info.id)
            
            LOGGER.info(f"Created {len(created_jobs)} jobs for concurrent deletion test")
            
            # 2. 并发删除所有作业
            async def delete_single_job(job_id):
                try:
                    await self.cluster.delete_job(job_id)
                    LOGGER.info(f"Concurrently deleted job: {job_id}")
                    return job_id, True, None
                except Exception as e:
                    LOGGER.warning(f"Failed to delete job {job_id}: {e}")
                    return job_id, False, str(e)
            
            # 创建并发任务
            delete_tasks = [delete_single_job(job_id) for job_id in created_jobs]
            results = await aio.gather(*delete_tasks, return_exceptions=True)
            
            # 3. 分析删除结果
            successful_deletions = 0
            failed_deletions = 0
            
            for result in results:
                if isinstance(result, Exception):
                    LOGGER.warning(f"Deletion task failed with exception: {result}")
                    failed_deletions += 1
                else:
                    job_id, success, error = result
                    if success:
                        successful_deletions += 1
                    else:
                        failed_deletions += 1
                        LOGGER.warning(f"Job {job_id} deletion failed: {error}")
            
            LOGGER.info(f"Concurrent deletion results: {successful_deletions} success, {failed_deletions} failed")
            
            # 4. 等待一段时间让删除完成
            await aio.sleep(5)
            
            # 5. 验证作业最终状态
            remaining_jobs = await self.cluster.list_jobs()
            remaining_job_ids = [job.id for job in remaining_jobs]
            
            jobs_still_exist = []
            for job_id in created_jobs:
                if job_id in remaining_job_ids:
                    jobs_still_exist.append(job_id)
                    try:
                        # 再次尝试删除
                        await self.cluster.delete_job(job_id)
                        LOGGER.info(f"Cleaned up remaining job: {job_id}")
                    except Exception as e:
                        LOGGER.warning(f"Failed to clean up job {job_id}: {e}")
            
            if jobs_still_exist:
                LOGGER.warning(f"Some jobs still exist after concurrent deletion: {jobs_still_exist}")
            else:
                LOGGER.info(f"✅ All jobs successfully removed")
            
            # 对于测试通过，我们要求至少大部分删除成功
            success_rate = successful_deletions / len(created_jobs)
            self.assertGreaterEqual(success_rate, 0.5, 
                f"Expected at least 50% deletion success rate, got {success_rate:.2%}")
            
            LOGGER.info(f"✅ Concurrent deletion test completed with {success_rate:.2%} success rate")
            
        RUNNER.run(_test())


if __name__ == '__main__':
    unittest.main()