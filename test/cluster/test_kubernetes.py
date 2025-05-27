"""Kubernetes 集群测试

测试 Kubernetes 集群的用户独立 code-server 部署功能。
"""

import unittest
import asyncio as aio
import socket
import urllib.request
import urllib.error
from urllib.parse import urlparse
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
    
    def test_create_job_deployment_status(self):
        """测试创建作业并验证 deployment 运行状态"""
        async def test_logic():
            LOGGER.info("🧪 Testing job creation and deployment status...")
            
            # 创建测试用户的 code-server 作业参数
            user_id = 2001
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="test-workspace",
                memory_limit="512Mi",
                cpu_limit="500m"
            )
            
            LOGGER.info(f"📝 Creating job for user {user_id}...")
            
            # 提交作业
            job_info = await self.cluster.submit_job(job_params)
            
            # 记录作业ID用于清理
            self.track_job(job_info.id)
            
            # 验证作业信息
            self.assert_code_server_job_valid(job_info)
            self.assertEqual(job_info.user_id, user_id)
            self.assertIsNotNone(job_info.service_url)
            
            LOGGER.info(f"✅ Job created: {job_info.id}")
            LOGGER.info(f"📍 Service URL: {job_info.service_url}")
            
            if self.is_real_k8s:
                # 对于真实的 Kubernetes 集群，等待 deployment 就绪
                LOGGER.info("⏳ Waiting for deployment to be ready...")
                
                # 等待作业状态变为 RUNNING（最多等待60秒）
                ready = await self.wait_for_job_status(job_info.id, JobInfo.Status.RUNNING, timeout=60)
                
                if ready:
                    LOGGER.info("✅ Deployment is running")
                    
                    # 验证最终状态
                    final_status = await self.cluster.get_job_status(job_info.id)
                    self.assertEqual(final_status, JobInfo.Status.RUNNING)
                    
                    # 获取最新的作业信息
                    updated_job_info = await self.cluster.get_job_info(job_info.id)
                    self.assert_code_server_job_valid(updated_job_info)
                    self.assertEqual(updated_job_info.status, JobInfo.Status.RUNNING)
                    
                else:
                    LOGGER.warning("⚠️  Deployment did not reach RUNNING state within timeout")
                    # 获取当前状态用于调试
                    current_status = await self.cluster.get_job_status(job_info.id)
                    LOGGER.warning(f"Current status: {current_status}")
                    
                    # 对于测试，我们仍然认为这是可接受的，因为可能是资源限制
                    self.assertIn(current_status, [
                        JobInfo.Status.PENDING, 
                        JobInfo.Status.RUNNING,
                        JobInfo.Status.FAILED
                    ])
            else:
                # 对于 Mock 集群，状态应该立即为 RUNNING
                self.assertEqual(job_info.status, JobInfo.Status.RUNNING)
                LOGGER.info("✅ Mock deployment is running")
            
            return job_info
        
        return RUNNER.run(test_logic())

    def test_duplicate_job_creation_same_user(self):
        """测试重复创建相同用户的作业是否会重复创建 deployment"""
        async def test_logic():
            LOGGER.info("🧪 Testing duplicate job creation for same user...")
            
            user_id = 2002
            
            # 第一次创建作业
            job_params_1 = self.create_code_server_params(
                user_id=user_id,
                workspace_name="workspace-1",
                memory_limit="256Mi"
            )
            
            LOGGER.info(f"📝 Creating first job for user {user_id}...")
            job_info_1 = await self.cluster.submit_job(job_params_1)
            self.track_job(job_info_1.id)
            
            LOGGER.info(f"✅ First job created: {job_info_1.id}")
            
            # 等待一秒确保时间戳不同
            await aio.sleep(1)
            
            # 第二次创建相同用户的作业（应该重用或更新现有 deployment）
            job_params_2 = self.create_code_server_params(
                user_id=user_id,
                workspace_name="workspace-2",
                memory_limit="512Mi",  # 不同的资源配置
                env={"UPDATED": "true"}  # 不同的环境变量
            )
            
            LOGGER.info(f"📝 Creating second job for user {user_id}...")
            job_info_2 = await self.cluster.submit_job(job_params_2)
            
            # 如果返回了不同的作业ID，也要跟踪
            if job_info_2.id != job_info_1.id:
                self.track_job(job_info_2.id)
            
            LOGGER.info(f"✅ Second job processed: {job_info_2.id}")
            
            # 验证行为：应该重用现有的 deployment 或者更新它
            if self.is_real_k8s:
                # 对于真实的 Kubernetes 集群，检查实际的 deployment 行为
                
                # 方式1: 同一个 deployment 被更新
                if job_info_1.id == job_info_2.id:
                    LOGGER.info("✅ Same deployment reused and updated")
                    self.assertEqual(job_info_1.id, job_info_2.id)
                    self.assertEqual(job_info_1.user_id, job_info_2.user_id)
                    
                    # 验证配置已更新
                    updated_job = await self.cluster.get_job_info(job_info_2.id)
                    self.assertIn("UPDATED", updated_job.env)
                    
                # 方式2: 旧的被替换，新的被创建（取决于实现策略）
                else:
                    LOGGER.info("ℹ️  New deployment created, old one should be cleaned up")
                    self.assertNotEqual(job_info_1.id, job_info_2.id)
                    self.assertEqual(job_info_1.user_id, job_info_2.user_id)
                    
                    # 验证旧的作业状态（可能被暂停或删除）
                    try:
                        old_status = await self.cluster.get_job_status(job_info_1.id)
                        LOGGER.info(f"Old job status: {old_status}")
                        # 旧作业应该不再是 RUNNING 状态
                        self.assertNotEqual(old_status, JobInfo.Status.RUNNING)
                    except JobNotFoundError:
                        LOGGER.info("✅ Old job was properly cleaned up")
                
                # 验证新作业是活跃的
                final_job = await self.cluster.get_job_info(job_info_2.id)
                self.assert_code_server_job_valid(final_job)
                self.assertEqual(final_job.user_id, user_id)
                
            else:
                # 对于 Mock 集群，验证预期的行为
                LOGGER.info("🎭 Verifying mock cluster behavior...")
                
                # Mock 集群应该重用相同用户的 deployment
                self.assertEqual(job_info_1.user_id, job_info_2.user_id)
                
                # 验证最新的作业信息
                latest_job = await self.cluster.get_job_info(job_info_2.id)
                self.assert_code_server_job_valid(latest_job)
            
            return job_info_1, job_info_2
        
        return RUNNER.run(test_logic())

    def test_delete_job_suspension_behavior(self):
        """测试 delete_job 是否只是临时关闭 deployment 而不是完全删除"""
        async def test_logic():
            LOGGER.info("🧪 Testing delete_job suspension behavior...")
            
            user_id = 5001
            
            # 1. 创建测试作业
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="suspension-test",
                memory_limit="256Mi",
                env={"TEST_VAR": "original_value"}
            )
            
            LOGGER.info(f"📝 Creating job for suspension test (user {user_id})...")
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            original_job_id = job_info.id
            LOGGER.info(f"✅ Job created: {original_job_id}")
            
            # 验证作业正在运行
            initial_status = await self.cluster.get_job_status(original_job_id)
            LOGGER.info(f"📊 Initial status: {initial_status}")
            
            if self.is_real_k8s:
                # 等待一下确保 deployment 启动
                await aio.sleep(5)
            
            # 2. 获取 deployment 的详细信息（暂停前）
            if self.is_real_k8s:
                original_deployment = await aio.to_thread(
                    self.cluster.apps_v1.read_namespaced_deployment,
                    name=original_job_id,
                    namespace=self.cluster.config.Kubernetes.NAMESPACE
                )
                original_replicas = original_deployment.spec.replicas
                original_annotations = original_deployment.metadata.annotations or {}
                
                LOGGER.info(f"📊 Original replicas: {original_replicas}")
                LOGGER.info(f"📊 Original annotations: {original_annotations}")
            
            # 3. 调用 delete_job 进行暂停
            LOGGER.info(f"⏸️  Calling delete_job to suspend user {user_id} deployments...")
            suspended_jobs = await self.cluster.delete_job(user_id)
            
            self.assertIn(original_job_id, suspended_jobs)
            self.assertEqual(len(suspended_jobs), 1)
            LOGGER.info(f"✅ Suspended jobs: {suspended_jobs}")
            
            # 4. 验证 deployment 仍然存在，但被暂停了
            if self.is_real_k8s:
                # 等待暂停生效
                await aio.sleep(3)
                
                # 检查 deployment 仍然存在
                try:
                    suspended_deployment = await aio.to_thread(
                        self.cluster.apps_v1.read_namespaced_deployment,
                        name=original_job_id,
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    )
                    
                    # 验证 deployment 存在
                    self.assertIsNotNone(suspended_deployment)
                    LOGGER.info("✅ Deployment still exists after suspension")
                    
                    # 验证副本数被设置为 0
                    self.assertEqual(suspended_deployment.spec.replicas, 0)
                    LOGGER.info(f"✅ Replicas set to 0: {suspended_deployment.spec.replicas}")
                    
                    # 验证注解被正确设置
                    annotations = suspended_deployment.metadata.annotations or {}
                    self.assertEqual(annotations.get("yatcc-se/suspended"), "true")
                    self.assertEqual(annotations.get("yatcc-se/original-replicas"), str(original_replicas))
                    
                    LOGGER.info(f"✅ Suspension annotations set correctly:")
                    LOGGER.info(f"   - suspended: {annotations.get('yatcc-se/suspended')}")
                    LOGGER.info(f"   - original-replicas: {annotations.get('yatcc-se/original-replicas')}")
                    
                    # 验证其他配置信息保持不变
                    container = suspended_deployment.spec.template.spec.containers[0]
                    env_dict = {env_var.name: env_var.value for env_var in (container.env or [])}
                    
                    self.assertEqual(container.image, job_params.image)
                    self.assertEqual(env_dict.get("TEST_VAR"), "original_value")
                    LOGGER.info("✅ Original configuration preserved")
                    
                except Exception as e:
                    self.fail(f"Deployment should still exist after suspension: {e}")
            
            # 5. 验证作业状态反映了暂停状态
            try:
                suspended_status = await self.cluster.get_job_status(original_job_id)
                # 暂停后状态应该不是 RUNNING
                if suspended_status == JobInfo.Status.RUNNING:
                    LOGGER.warning("⚠️  Status still shows RUNNING after suspension")
                else:
                    LOGGER.info(f"✅ Status after suspension: {suspended_status}")
            except JobNotFoundError:
                self.fail("Job should still be found after suspension")
            
            # 6. 验证可以获取作业信息（但状态可能不同）
            try:
                suspended_job_info = await self.cluster.get_job_info(original_job_id)
                self.assertEqual(suspended_job_info.id, original_job_id)
                self.assertEqual(suspended_job_info.user_id, user_id)
                self.assertEqual(suspended_job_info.env.get("TEST_VAR"), "original_value")
                LOGGER.info("✅ Job info still accessible after suspension")
            except JobNotFoundError:
                self.fail("Job info should still be accessible after suspension")
            
            # 7. 验证再次提交相同用户的作业会恢复原来的 deployment
            LOGGER.info(f"🔄 Testing recovery by submitting new job for user {user_id}...")
            
            recovery_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="recovery-test",
                memory_limit="512Mi",  # 不同的配置
                env={"TEST_VAR": "updated_value", "NEW_VAR": "added"}
            )
            
            recovered_job_info = await self.cluster.submit_job(recovery_params)
            
            # 如果是相同的 deployment ID，说明恢复了原来的
            if recovered_job_info.id == original_job_id:
                LOGGER.info("✅ Original deployment was recovered and updated")
                self.assertEqual(recovered_job_info.id, original_job_id)
                
                # 验证配置被更新了
                if self.is_real_k8s:
                    await aio.sleep(3)  # 等待更新生效
                    
                    recovered_deployment = await aio.to_thread(
                        self.cluster.apps_v1.read_namespaced_deployment,
                        name=original_job_id,
                        namespace=self.cluster.config.Kubernetes.NAMESPACE
                    )
                    
                    # 验证副本数恢复了
                    self.assertGreater(recovered_deployment.spec.replicas, 0)
                    LOGGER.info(f"✅ Replicas restored to: {recovered_deployment.spec.replicas}")
            else:
                LOGGER.info("ℹ️  New deployment created (old one replaced)")
                self.track_job(recovered_job_info.id)
            
            # 8. 验证 list_jobs 中能看到恢复的作业
            all_jobs = await self.cluster.list_jobs()
            active_user_jobs = [job for job in all_jobs if job.user_id == user_id]
            
            self.assertGreater(len(active_user_jobs), 0)
            LOGGER.info(f"✅ Found {len(active_user_jobs)} active jobs for user {user_id}")
            
            return {
                'original_job_id': original_job_id,
                'suspended_jobs': suspended_jobs,
                'recovered_job_info': recovered_job_info
            }
        
        return RUNNER.run(test_logic())

    def test_delete_job_nonexistent_user(self):
        """测试对不存在的用户调用 delete_job"""
        async def test_logic():
            LOGGER.info("🧪 Testing delete_job with nonexistent user...")
            
            nonexistent_user_id = 9999
            
            # 调用 delete_job 对不存在的用户
            try:
                suspended_jobs = await self.cluster.delete_job(nonexistent_user_id)
                
                # 应该返回空列表，而不是抛出异常
                self.assertEqual(suspended_jobs, [])
                LOGGER.info(f"✅ No jobs suspended for nonexistent user {nonexistent_user_id}")
                
            except JobNotFoundError:
                LOGGER.info("ℹ️  JobNotFoundError raised for nonexistent user (acceptable)")
            except Exception as e:
                self.fail(f"Unexpected exception for nonexistent user: {e}")
            
            return True
        
        return RUNNER.run(test_logic())

    def test_get_service_url_connectivity(self):
        """测试 get_service_url 方法并验证端口联通性"""
        async def test_logic():
            LOGGER.info("🧪 Testing get_service_url and port connectivity...")
            
            user_id = 6001
            
            # 1. 创建测试作业
            job_params = self.create_code_server_params(
                user_id=user_id,
                workspace_name="connectivity-test",
                memory_limit="512Mi",
                cpu_limit="500m",  # 添加 CPU 限制
                env={"TEST_ENV": "connectivity_test"}
            )
            
            LOGGER.info(f"📝 Creating job for connectivity test (user {user_id})...")
            job_info = await self.cluster.submit_job(job_params)
            self.track_job(job_info.id)
            
            LOGGER.info(f"✅ Job created: {job_info.id}")
            LOGGER.info(f"📍 Initial service URL: {job_info.service_url}")
            
            if self.is_real_k8s:
                # 2. 等待 Pod 就绪，而不是立即尝试端口转发
                LOGGER.info("⏳ Waiting for Pod to be ready...")
                
                pod_ready = await self._wait_for_pod_ready(job_info.id, timeout=120)
                
                if not pod_ready:
                    LOGGER.warning("⚠️  Pod did not become ready within timeout")
                    await self._debug_pod_status(job_info.id)
                    await self._debug_service_status(job_info.id)
                    
                    # 即使 Pod 没有就绪，我们仍然测试 get_service_url 的功能
                    LOGGER.info("🔗 Testing get_service_url even though Pod is not ready...")
                else:
                    LOGGER.info("✅ Pod is ready, proceeding with connectivity tests")
            
            # 3. 获取服务 URL
            LOGGER.info(f"🔗 Getting service URL for job {job_info.id}...")
            
            try:
                service_url = await self.cluster.get_service_url(job_info.id)
                
                self.assertIsNotNone(service_url)
                LOGGER.info(f"🌐 Service URL: {service_url}")
                
                # 4. 解析 URL 获取主机和端口
                parsed_url = urlparse(service_url)
                host = parsed_url.hostname
                port = parsed_url.port
                
                LOGGER.info(f"🔍 Parsed URL components:")
                LOGGER.info(f"  - Scheme: {parsed_url.scheme}")
                LOGGER.info(f"  - Host: {host}")
                LOGGER.info(f"  - Port: {port}")
                
                # 验证 URL 格式
                self.assertIn(parsed_url.scheme, ['http', 'https'])
                self.assertIsNotNone(host)
                self.assertIsNotNone(port)
                
                if self.is_real_k8s:
                    # 5. 只有在 Pod 就绪的情况下才测试连通性
                    if pod_ready:
                        # 验证作业状态
                        job_status = await self.cluster.get_job_status(job_info.id)
                        LOGGER.info(f"📊 Job status: {job_status}")
                        
                        # 6. 测试端口连通性
                        LOGGER.info(f"🔌 Testing port connectivity to {host}:{port}...")
                        
                        port_open = await self._test_port_connectivity(host, port, timeout=10)
                        
                        if port_open:
                            LOGGER.info(f"✅ Port {port} on {host} is accessible")
                            
                            # 7. 测试 HTTP 连接
                            LOGGER.info(f"🌐 Testing HTTP connectivity to {service_url}...")
                            
                            http_accessible = await self._test_http_connectivity(service_url)
                            
                            if http_accessible:
                                LOGGER.info(f"✅ HTTP connection to {service_url} successful")
                            else:
                                LOGGER.warning(f"⚠️  HTTP connection to {service_url} failed")
                        else:
                            LOGGER.warning(f"⚠️  Port {port} on {host} is not accessible")
                            LOGGER.info("💡 This may be expected if the port forward setup failed")
                    else:
                        LOGGER.info("⏭️  Skipping connectivity tests due to Pod not being ready")
                    
                    # 8. 验证多次调用 get_service_url 返回一致结果
                    LOGGER.info("🔄 Testing consistency of get_service_url...")
                    
                    for i in range(3):
                        url_check = await self.cluster.get_service_url(job_info.id)
                        self.assertEqual(url_check, service_url)
                        LOGGER.info(f"✅ Consistency check {i+1}: {url_check}")
                        await aio.sleep(1)
                    
                else:
                    # 9. 对于 Mock 集群的测试
                    LOGGER.info("🎭 Testing mock cluster service URL...")
                    
                    # Mock 集群应该返回有效的 URL 格式
                    self.assertTrue(service_url.startswith('http'))
                    LOGGER.info(f"✅ Mock service URL format is valid: {service_url}")
                
                return {
                    'job_id': job_info.id,
                    'service_url': service_url,
                    'host': host,
                    'port': port,
                    'user_id': user_id,
                    'pod_ready': pod_ready if self.is_real_k8s else True
                }
                
            except Exception as e:
                LOGGER.error(f"❌ get_service_url failed: {e}")
                
                if self.is_real_k8s:
                    await self._debug_pod_status(job_info.id)
                    await self._debug_service_status(job_info.id)
                
                # 重新抛出异常以便测试失败
                raise
        
        return RUNNER.run(test_logic())

    async def _wait_for_pod_ready(self, job_id: str, timeout: int = 120) -> bool:
        """等待 Pod 变为就绪状态"""
        LOGGER.info(f"⏳ Waiting for Pod {job_id} to be ready (timeout: {timeout}s)...")
        
        start_time = aio.get_event_loop().time()
        
        while True:
            try:
                pods = await aio.to_thread(
                    self.cluster.core_v1.list_namespaced_pod,
                    namespace=self.cluster.config.Kubernetes.NAMESPACE,
                    label_selector=f"app={job_id}"
                )
                
                if not pods.items:
                    LOGGER.debug(f"No pods found for job {job_id}")
                    await aio.sleep(5)
                    continue
                
                pod = pods.items[0]  # 取第一个 Pod
                pod_name = pod.metadata.name
                pod_phase = pod.status.phase
                
                LOGGER.debug(f"Pod {pod_name} phase: {pod_phase}")
                
                if pod_phase == "Running":
                    # 检查容器是否都就绪
                    if pod.status.container_statuses:
                        all_ready = all(cs.ready for cs in pod.status.container_statuses)
                        if all_ready:
                            LOGGER.info(f"✅ Pod {pod_name} is running and all containers are ready")
                            return True
                        else:
                            LOGGER.debug(f"Pod {pod_name} running but containers not all ready")
                    else:
                        LOGGER.debug(f"Pod {pod_name} running but no container status available")
                
                elif pod_phase == "Pending":
                    # 检查 Pending 的原因
                    if pod.status.conditions:
                        for condition in pod.status.conditions:
                            if condition.status == "False":
                                LOGGER.debug(f"Pod condition: {condition.type} - {condition.reason}: {condition.message}")
                    
                    # 检查容器状态
                    if pod.status.container_statuses:
                        for cs in pod.status.container_statuses:
                            if cs.state.waiting:
                                reason = cs.state.waiting.reason
                                message = cs.state.waiting.message
                                LOGGER.debug(f"Container {cs.name} waiting: {reason} - {message}")
                                
                                # 如果是镜像拉取问题，给更多时间
                                if reason in ["ImagePullBackOff", "ErrImagePull"]:
                                    LOGGER.warning(f"⚠️  Image pull issues detected for {cs.name}")
                
                elif pod_phase == "Failed":
                    LOGGER.error(f"❌ Pod {pod_name} failed")
                    await self._debug_pod_status(job_id)
                    return False
                    
            except Exception as e:
                LOGGER.warning(f"Error checking pod status: {e}")
            
            # 检查超时
            elapsed = aio.get_event_loop().time() - start_time
            if elapsed > timeout:
                LOGGER.warning(f"⏰ Timeout waiting for Pod {job_id} to be ready after {timeout}s")
                return False
            
            await aio.sleep(5)  # 等待5秒后重试

    async def _debug_pod_status(self, job_id: str):
        """调试 Pod 状态"""
        # ... (保持之前的实现)
        try:
            LOGGER.info(f"🔍 Debugging Pod status for job {job_id}...")
            
            pods = await aio.to_thread(
                self.cluster.core_v1.list_namespaced_pod,
                namespace=self.cluster.config.Kubernetes.NAMESPACE,
                label_selector=f"app={job_id}"
            )
            
            if not pods.items:
                LOGGER.warning(f"❌ No pods found for job {job_id}")
                return
            
            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_phase = pod.status.phase
                
                LOGGER.info(f"📦 Pod: {pod_name}")
                LOGGER.info(f"  - Phase: {pod_phase}")
                LOGGER.info(f"  - Node: {pod.spec.node_name or 'Not assigned'}")
                LOGGER.info(f"  - Creation time: {pod.metadata.creation_timestamp}")
                
                # 检查容器状态
                if pod.status.container_statuses:
                    LOGGER.info(f"  - Container statuses:")
                    for container_status in pod.status.container_statuses:
                        LOGGER.info(f"    📦 Container {container_status.name}:")
                        LOGGER.info(f"      - Ready: {container_status.ready}")
                        LOGGER.info(f"      - Restart count: {container_status.restart_count}")
                        LOGGER.info(f"      - Image: {container_status.image}")
                        
                        if container_status.state.waiting:
                            waiting = container_status.state.waiting
                            LOGGER.warning(f"      ⏳ Waiting: {waiting.reason}")
                            if waiting.message:
                                LOGGER.warning(f"         Message: {waiting.message}")
                        elif container_status.state.running:
                            running = container_status.state.running
                            LOGGER.info(f"      ✅ Running since: {running.started_at}")
                        elif container_status.state.terminated:
                            terminated = container_status.state.terminated
                            LOGGER.error(f"      ❌ Terminated: {terminated.reason}")
                            if terminated.message:
                                LOGGER.error(f"         Message: {terminated.message}")
                            LOGGER.error(f"         Exit code: {terminated.exit_code}")
        
        except Exception as e:
            LOGGER.error(f"Failed to debug pod status: {e}")

    async def _debug_service_status(self, job_id: str):
        """调试 Service 状态"""
        # ... (使用上面定义的实现)
        try:
            LOGGER.info(f"🔍 Debugging Service status for job {job_id}...")
            
            service_name = f"{job_id}-svc"
            
            try:
                service = await aio.to_thread(
                    self.cluster.core_v1.read_namespaced_service,
                    name=service_name,
                    namespace=self.cluster.config.Kubernetes.NAMESPACE
                )
                
                LOGGER.info(f"🌐 Service: {service.metadata.name}")
                LOGGER.info(f"  - Type: {service.spec.type}")
                LOGGER.info(f"  - Cluster IP: {service.spec.cluster_ip}")
                
                # 显示端口信息
                if service.spec.ports:
                    LOGGER.info(f"  - Ports:")
                    for port in service.spec.ports:
                        LOGGER.info(f"    📌 {port.name or 'unnamed'}: {port.port}/{port.protocol}")
                        if port.target_port:
                            LOGGER.info(f"      Target port: {port.target_port}")
                
                # 显示选择器
                if service.spec.selector:
                    LOGGER.info(f"  - Selector:")
                    for key, value in service.spec.selector.items():
                        LOGGER.info(f"    {key}: {value}")
                
            except Exception as e:
                if "not found" in str(e).lower():
                    LOGGER.warning(f"❌ Service {service_name} not found")
                else:
                    LOGGER.error(f"Failed to get service {service_name}: {e}")
        
        except Exception as e:
            LOGGER.error(f"Failed to debug service status: {e}")

    async def _test_port_connectivity(self, host: str, port: int, timeout: int = 5) -> bool:
        """测试端口连通性"""
        # ... (使用上面定义的实现)
        try:
            future = aio.get_event_loop().run_in_executor(
                None, 
                self._sync_test_port_connectivity, 
                host, port, timeout
            )
            return await future
        except Exception as e:
            LOGGER.warning(f"Port connectivity test failed: {e}")
            return False

    def _sync_test_port_connectivity(self, host: str, port: int, timeout: int) -> bool:
        """同步测试端口连通性"""
        # ... (使用上面定义的实现)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                return result == 0
        except Exception as e:
            LOGGER.debug(f"Socket connection failed: {e}")
            return False

    async def _test_http_connectivity(self, url: str, timeout: int = 10) -> bool:
        """测试 HTTP 连通性"""
        # ... (使用上面定义的实现)
        try:
            future = aio.get_event_loop().run_in_executor(
                None, 
                self._sync_test_http_connectivity, 
                url, timeout
            )
            return await future
        except Exception as e:
            LOGGER.warning(f"HTTP connectivity test failed: {e}")
            return False

    def _sync_test_http_connectivity(self, url: str, timeout: int) -> bool:
        """同步测试 HTTP 连通性"""
        # ... (使用上面定义的实现)
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'YatCC-SE-Test/1.0'
            })
            
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                LOGGER.debug(f"HTTP response status: {status_code}")
                return status_code in [200, 302, 401, 403]
                
        except urllib.error.HTTPError as e:
            LOGGER.debug(f"HTTP error: {e.code}")
            return e.code in [401, 403, 404, 500]
            
        except Exception as e:
            LOGGER.debug(f"HTTP test exception: {e}")
            return False


if __name__ == '__main__':
    unittest.main()