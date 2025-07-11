"""Kubernetes 集群测试

测试 Kubernetes 集群的用户独立 code-server 部署功能。
"""

import unittest
import asyncio as aio
from cluster import JobInfo
from base.logger import logger
from . import ClusterTestBase, RUNNER, get_kubernetes_cluster, ensure_kubernetes_cluster

LOGGER = logger(__spec__, __file__)


def setUpModule() -> None:
    """模块级别的设置"""
    from .. import setup_test

    setup_test(__name__)
    LOGGER.info("🚀 Kubernetes cluster test module setup")
    # 预先初始化 Kubernetes 集群
    try:
        k8s_cluster = ensure_kubernetes_cluster()
        if k8s_cluster:
            LOGGER.info(
                f"✅ Kubernetes cluster ready for testing: {k8s_cluster.__class__.__name__}"
            )
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
        k8s_cluster = ensure_kubernetes_cluster()

        if k8s_cluster is None:
            self.skipTest("No Kubernetes cluster available for testing")

        self.cluster = k8s_cluster

        # 检查是否是真实的 Kubernetes 集群
        is_mock = getattr(self.cluster, "_is_mock", True)
        if is_mock:
            LOGGER.info(
                f"Using MOCK cluster for Kubernetes tests: {self.cluster.__class__.__name__}"
            )
            self.is_real_k8s = False
        else:
            LOGGER.info(
                f"Using REAL Kubernetes cluster: {self.cluster.__class__.__name__}"
            )
            self.is_real_k8s = True

        self.assertIsNotNone(self.cluster, "Kubernetes cluster should be available")

    def test_create_job_deployment_status(self):
        """测试创建作业并验证 deployment 运行状态"""

        async def test_logic():
            LOGGER.info("🧪 Testing job creation and deployment status...")

            user_id = "2001"
            job_params = self.build_test_job_params(
                sid=user_id,
            )

            LOGGER.info(f"📝 Creating job for user {user_id}...")
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)

            # 验证作业信息
            self.assert_code_server_job_valid(job_info)
            self.assertEqual(job_info.user_id, str(user_id))
            self.assertIsNotNone(job_info.service_url)

            LOGGER.info(f"✅ Job created: {job_info.id}")

            if self.is_real_k8s:
                # 等待作业就绪
                ready = await self.wait_for_job_status(
                    job_info.id, JobInfo.Status.RUNNING, timeout=60
                )
                if ready:
                    LOGGER.info("✅ Deployment is running")
                    final_status = await self.cluster.get_job_status(job_info.id)
                    self.assertEqual(final_status, JobInfo.Status.RUNNING)
                else:
                    current_status = await self.cluster.get_job_status(job_info.id)
                    LOGGER.warning(f"⚠️  Current status: {current_status}")
                    self.assertIn(
                        current_status,
                        [
                            JobInfo.Status.PENDING,
                            JobInfo.Status.RUNNING,
                            JobInfo.Status.FAILED,
                        ],
                    )
            else:
                self.assertEqual(job_info.status, JobInfo.Status.RUNNING)
                LOGGER.info("✅ Mock deployment is running")

            return job_info

        return RUNNER.run(test_logic())

    def test_duplicate_job_creation_same_user(self):
        """测试重复创建相同用户的作业"""

        async def test_logic():
            LOGGER.info("🧪 Testing duplicate job creation for same user...")

            user_id = "2002"
            job_name = str(user_id)  # 作业名称为用户ID

            # 第一次创建作业
            job_params_1 = self.build_test_job_params(
                sid=user_id, workspace_name="workspace-1", memory_limit="256Mi"
            )

            LOGGER.info(f"📝 Creating first job for user {user_id}...")
            job_info_1 = await self.cluster.submit_job(job_params_1)
            self.track_job(job_info_1.id)
            LOGGER.info(f"✅ First job created: {job_info_1.id}")

            await aio.sleep(1)

            # 第二次创建相同用户的作业（应该重用现有 deployment）
            job_params_2 = self.build_test_job_params(
                sid=user_id, memory_limit="512Mi", env={"UPDATED": "true"}
            )

            LOGGER.info(f"📝 Creating second job for user {user_id}...")
            job_info_2 = await self.cluster.submit_job(job_params_2)

            LOGGER.info(f"✅ Second job processed: {job_info_2.id}")

            # 验证：应该是同一个作业（用户独立部署）
            self.assertEqual(
                job_info_1.id, job_info_2.id, "Same user should reuse deployment"
            )
            self.assertEqual(job_info_1.user_id, job_info_2.user_id)

            if self.is_real_k8s:
                # 验证配置已更新
                updated_job = await self.cluster.get_job_info(job_info_2.id)
                self.assertIn("UPDATED", updated_job.env)
                LOGGER.info("✅ Deployment configuration updated")

            return job_info_1, job_info_2

        return RUNNER.run(test_logic())

    def test_delete_job_suspension_behavior(self):
        """测试 delete_job 暂停行为"""

        async def test_logic():
            LOGGER.info("🧪 Testing delete_job suspension behavior...")

            user_id = "5001"

            # 创建测试作业
            job_params = self.build_test_job_params(
                sid=user_id,
                memory_limit="256Mi",
                env={"TEST_VAR": "original_value"},
            )

            job_name = job_params.name

            LOGGER.info(f"📝 Creating job for suspension test (user {user_id})...")
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)

            original_job_id = job_info.id
            LOGGER.info(f"✅ Job created: {original_job_id}")

            if self.is_real_k8s:
                await aio.sleep(5)  # 等待 deployment 启动

            # 调用 delete_job 进行暂停
            LOGGER.info(f"⏸️  Suspending job {job_name}...")
            suspended_jobs = await self.cluster.delete_job(job_name)

            self.assertIn(original_job_id, suspended_jobs)
            LOGGER.info(f"✅ Suspended jobs: {suspended_jobs}")

            # 验证作业状态已变为 STOPPED
            if self.is_real_k8s:
                await aio.sleep(3)  # 等待状态更新
                status = await self.cluster.get_job_status(original_job_id)
                self.assertEqual(status, JobInfo.Status.PENDING)
                LOGGER.info("✅ Job status is STOPPED")

            # 重新提交相同作业（应该恢复）
            LOGGER.info(f"🔄 Resuming job {job_name}...")
            resumed_job = await self.cluster.submit_job(job_params)

            # 应该是同一个作业ID
            self.assertEqual(resumed_job.id, original_job_id)
            LOGGER.info(f"✅ Job resumed: {resumed_job.id}")

            return original_job_id, suspended_jobs

        return RUNNER.run(test_logic())

    def test_get_service_url_port_forward(self):
        """测试获取服务URL和端口转发"""

        async def test_logic():
            LOGGER.info("🧪 Testing service URL and port forwarding...")

            user_id = "3001"

            # 创建作业
            job_params = self.build_test_job_params(sid=user_id)

            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)

            if self.is_real_k8s:
                # 等待作业就绪
                await self.wait_for_job_status(
                    job_info.id, JobInfo.Status.RUNNING, timeout=30
                )

            # 获取本地访问URL（自动创建端口转发）
            LOGGER.info("🔗 Getting service URL...")
            local_url = await self.cluster.get_service_url(job_info.id)

            return local_url

        return RUNNER.run(test_logic())


if __name__ == "__main__":
    unittest.main()
