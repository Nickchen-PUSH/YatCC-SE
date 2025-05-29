import core
from base.logger import logger
import core.student

from .. import RUNNER, AsyncTestCase

LOGGER = logger(__spec__, __file__)


def setUpModule() -> None:
    from .. import setup_test, ainit_core

    setup_test(__name__)
    RUNNER.run(ainit_core())


def tearDownModule() -> None:
    return


class TableTest(AsyncTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        return

    @classmethod
    def tearDownClass(cls) -> None:
        return

    def setUp(self) -> None:
        return

    def tearDown(self) -> None:
        return

    async def test_create_and_delete(self):
        from core.student import TABLE, Student, UserInfo

        stu = Student(
            sid="22335009",
            pwd_hash="1234567890abcdef",
            user_info=UserInfo(name="Haoquan Chen", mail="chenhq79@mail2.sysu.edu.cn"),
            codespace=core.student.CodespaceInfo(),
        )

        self.assertTrue(await TABLE.create(stu))
        LOGGER.info("Created student record: %s", stu)
        read_stu = await TABLE.read(stu.sid)
        LOGGER.info("Read student record: %s", read_stu)
        self.assertEqual(stu.sid, read_stu.sid)

        self.assertTrue(await TABLE.delete(stu.sid))
        LOGGER.info("Deleted student record: %s", stu.sid)
    
    async def test_check_password(self):
        from core.student import TABLE, Student, UserInfo
        from werkzeug.security import generate_password_hash
        
        # 创建测试学生，设置明文密码为"test_password"
        test_password = "test_password"
        pwd_hash = generate_password_hash(test_password)
        
        stu = Student(
            sid="22335010",
            pwd_hash=pwd_hash,
            user_info=UserInfo(name="Test User", mail="test@example.com"),
            codespace=core.student.CodespaceInfo(),
        )
        
        # 创建学生记录
        self.assertTrue(await TABLE.create(stu))
        LOGGER.info("Created test student for password check: %s", stu.sid)
        
        # 测试密码验证成功的情况
        self.assertTrue(await TABLE.check_password(stu.sid, test_password))
        LOGGER.info("Password check succeeded for correct password")
        
        # 测试密码验证失败的情况
        self.assertFalse(await TABLE.check_password(stu.sid, "wrong_password"))
        LOGGER.info("Password check failed for incorrect password")
        
        # 测试不存在的学生ID
        self.assertFalse(await TABLE.check_password("non_existent_sid", test_password))
        LOGGER.info("Password check failed for non-existent student")
        
        # 清理测试数据
        await TABLE.delete(stu.sid)
        LOGGER.info("Deleted test student: %s", stu.sid)
    
    async def test_get_user_info(self):
        from core.student import TABLE, Student, UserInfo
        
        # 创建测试学生
        test_name = "Test User"
        test_mail = "test@example.com"
        
        stu = Student(
            sid="22335011",
            pwd_hash="test_hash",
            user_info=UserInfo(name=test_name, mail=test_mail),
            codespace=core.student.CodespaceInfo(),
        )
        
        # 创建学生记录
        self.assertTrue(await TABLE.create(stu))
        LOGGER.info("Created test student for user info test: %s", stu.sid)
        
        # 获取并验证用户信息
        user_info = await TABLE.get_user_info(stu.sid)
        self.assertEqual(user_info.name, test_name)
        self.assertEqual(user_info.mail, test_mail)
        LOGGER.info("Successfully retrieved user info: %s", user_info)
        
        # 测试不存在的学生ID
        non_existent_info = await TABLE.get_user_info("non_existent_sid")
        self.assertEqual(non_existent_info.name, "")
        self.assertEqual(non_existent_info.mail, "")
        LOGGER.info("Retrieved empty user info for non-existent student")
        
        # 清理测试数据
        await TABLE.delete(stu.sid)
        LOGGER.info("Deleted test student: %s", stu.sid)
    
    async def test_set_user_info(self):
        from core.student import TABLE, Student, UserInfo, StudentNotFoundError
        
        # 创建测试学生
        stu = Student(
            sid="22335012",
            pwd_hash="test_hash",
            user_info=UserInfo(name="Initial Name", mail="initial@example.com"),
            codespace=core.student.CodespaceInfo(),
        )
        
        # 创建学生记录
        self.assertTrue(await TABLE.create(stu))
        LOGGER.info("Created test student for set user info test: %s", stu.sid)
        
        # 更新用户信息
        new_name = "Updated Name"
        new_mail = "updated@example.com"
        new_info = UserInfo(name=new_name, mail=new_mail)
        
        await TABLE.set_user_info(stu.sid, new_info)
        LOGGER.info("Updated user info for student: %s", stu.sid)
        
        # 验证更新是否成功
        updated_info = await TABLE.get_user_info(stu.sid)
        self.assertEqual(updated_info.name, new_name)
        self.assertEqual(updated_info.mail, new_mail)
        LOGGER.info("Successfully verified updated user info: %s", updated_info)
        
        # 测试更新不存在的学生信息
        with self.assertRaises(StudentNotFoundError):
            await TABLE.set_user_info("non_existent_sid", new_info)
        LOGGER.info("Correctly raised exception for non-existent student")
        
        # 清理测试数据
        await TABLE.delete(stu.sid)
        LOGGER.info("Deleted test student: %s", stu.sid)


class CodespaceTest(AsyncTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        return

    @classmethod
    def tearDownClass(cls) -> None:
        return

    def setUp(self) -> None:
        # 生成唯一测试ID
        import uuid
        self.test_id = f"test_{uuid.uuid4().hex[:8]}"
        return

    def tearDown(self) -> None:
        # 同步方法中不能直接调用异步删除，在test方法中自行清理
        return

    async def test_start_not_found(self):
        """测试启动不存在学生的代码空间"""
        from core.student import CODESPACE, StudentNotFoundError
        
        # 测试不存在的学生ID
        with self.assertRaises(StudentNotFoundError):
            await CODESPACE.start("non_existent_sid")
        LOGGER.info("成功测试: 启动不存在学生的代码空间抛出StudentNotFoundError")
    
    async def test_start_quota_exceeded(self):
        """测试配额已用尽的情况"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE, CodespaceQuotaExceededError
        
        # 创建测试学生，设置配额已用尽
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Codespace", mail="test@example.com"),
            codespace=CodespaceInfo(
                time_quota=3600,  # 1小时配额
                time_used=3600,   # 已用完配额
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 测试启动代码空间，应该抛出配额超限错误
            with self.assertRaises(CodespaceQuotaExceededError):
                await CODESPACE.start(stu.sid)
            LOGGER.info("成功测试: 启动配额超限的代码空间抛出CodespaceQuotaExceededError")
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_start_generic_error(self):
        """测试通用错误处理"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE, CodespaceStartError
        import unittest.mock as mock
        
        # 创建测试学生
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Codespace", mail="test@example.com"),
            codespace=CodespaceInfo(),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟CLUSTER.submit_job抛出异常
            with mock.patch('core.CLUSTER.submit_job', side_effect=Exception("模拟的集群错误")):
                with self.assertRaises(CodespaceStartError):
                    await CODESPACE.start(stu.sid)
            LOGGER.info("成功测试: 启动代码空间遇到一般错误时抛出CodespaceStartError")
            
            # 验证错误处理后学生的代码空间状态
            updated_stu = await TABLE.read(stu.sid)
            self.assertEqual(updated_stu.codespace.status, "stopped")
            LOGGER.info("成功验证: 错误处理后代码空间状态被设置为stopped")
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)

    async def test_start_success(self):
        """测试成功启动代码空间"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        
        # 创建测试学生
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Success", mail="test@example.com"),
            codespace=CodespaceInfo(
                time_quota=3600,  # 1小时配额
                time_used=0,      # 未使用配额
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 启动代码空间
            await CODESPACE.start(stu.sid)
            LOGGER.info("成功启动代码空间: %s", stu.sid)
            
            # 验证代码空间状态
            updated_stu = await TABLE.read(stu.sid)
            self.assertEqual(updated_stu.codespace.status, "running")
            self.assertTrue(updated_stu.codespace.url.startswith("http://"))
            self.assertGreater(updated_stu.codespace.last_start, 0)
            self.assertGreater(updated_stu.codespace.last_active, 0)
            
            # 验证Redis中是否存储了作业ID
            from core import DB_STU
            job_id = await DB_STU.get(f"{stu.sid}:job_id")
            self.assertIsNotNone(job_id)
            LOGGER.info("验证作业ID: %s", job_id)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)

    async def test_stop_not_found(self):
        """测试停止不存在学生的代码空间"""
        from core.student import CODESPACE, StudentNotFoundError
        
        # 测试不存在的学生ID
        with self.assertRaises(StudentNotFoundError):
            await CODESPACE.stop("non_existent_sid")
        LOGGER.info("成功测试: 停止不存在学生的代码空间抛出StudentNotFoundError")
    
    async def test_stop_already_stopped(self):
        """测试停止已经处于stopped状态的代码空间"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        
        # 创建测试学生，代码空间状态为stopped
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Stop", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="stopped",  # 已经是停止状态
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 调用停止方法
            await CODESPACE.stop(stu.sid)
            LOGGER.info("成功调用停止方法")
            
            # 验证状态仍然是stopped
            updated_stu = await TABLE.read(stu.sid)
            self.assertEqual(updated_stu.codespace.status, "stopped")
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_stop_no_job_id(self):
        """测试停止时找不到作业ID的情况"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        
        # 创建测试学生，代码空间状态为running但没有对应的作业ID
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Stop", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 调用停止方法
            await CODESPACE.stop(stu.sid)
            LOGGER.info("成功调用停止方法")
            
            # 验证状态已更新为stopped
            updated_stu = await TABLE.read(stu.sid)
            self.assertEqual(updated_stu.codespace.status, "stopped")
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_stop_success(self):
        """测试成功停止代码空间"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        from core import DB_STU
        from datetime import datetime
        import unittest.mock as mock
        
        # 创建测试学生，代码空间状态为running
        start_time = datetime.now().timestamp() - 3600  # 1小时前启动
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Stop", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
                last_start=start_time,
                time_used=1800,  # 已使用30分钟
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟作业ID
            job_id = "test_job_123"
            await DB_STU.set(f"{stu.sid}:job_id", job_id)
            LOGGER.info("设置作业ID: %s", job_id)
            
            # 使用mock模拟CLUSTER.delete_job，避免真实调用
            with mock.patch('core.CLUSTER.delete_job'):
                # 调用停止方法
                await CODESPACE.stop(stu.sid)
                LOGGER.info("成功调用停止方法")
            
            # 验证状态更新
            updated_stu = await TABLE.read(stu.sid)
            self.assertEqual(updated_stu.codespace.status, "stopped")
            self.assertEqual(updated_stu.codespace.url, "")
            self.assertGreater(updated_stu.codespace.last_stop, start_time)
            self.assertGreaterEqual(updated_stu.codespace.time_used, 1800)  # 使用时间应该至少等于原来的值
            
            # 验证作业ID是否被删除
            stored_job_id = await DB_STU.get(f"{stu.sid}:job_id")
            self.assertIsNone(stored_job_id)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            await DB_STU.delete(f"{stu.sid}:job_id")
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_stop_error(self):
        """测试停止代码空间时遇到错误"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE, CodespaceStopError
        from core import DB_STU
        import unittest.mock as mock
        
        # 创建测试学生，代码空间状态为running
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Stop", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟作业ID
            job_id = "test_job_456"
            await DB_STU.set(f"{stu.sid}:job_id", job_id)
            LOGGER.info("设置作业ID: %s", job_id)
            
            # 模拟CLUSTER.delete_job抛出异常
            with mock.patch('core.CLUSTER.delete_job', side_effect=Exception("模拟的集群错误")):
                with self.assertRaises(CodespaceStopError):
                    await CODESPACE.stop(stu.sid)
            LOGGER.info("成功测试: 停止代码空间遇到错误时抛出CodespaceStopError")
            
            # 验证错误处理后学生的代码空间状态
            updated_stu = await TABLE.read(stu.sid)
            self.assertEqual(updated_stu.codespace.status, "stopped")
            LOGGER.info("成功验证: 错误处理后代码空间状态被设置为stopped")
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            await DB_STU.delete(f"{stu.sid}:job_id")
            LOGGER.info("删除测试学生: %s", stu.sid)

    async def test_get_status_not_found(self):
        """测试获取不存在学生的代码空间状态"""
        from core.student import CODESPACE, StudentNotFoundError
        
        # 测试不存在的学生ID
        with self.assertRaises(StudentNotFoundError):
            await CODESPACE.get_status("non_existent_sid")
        LOGGER.info("成功测试: 获取不存在学生的代码空间状态抛出StudentNotFoundError")
    
    async def test_get_status_stopped(self):
        """测试获取stopped状态的代码空间状态"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        
        # 创建测试学生，代码空间状态为stopped
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Status", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="stopped",  # 已停止状态
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 获取状态
            status = await CODESPACE.get_status(stu.sid)
            self.assertEqual(status, "stopped")
            LOGGER.info("成功获取stopped状态: %s", status)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_status_running_no_job_id(self):
        """测试获取running状态但没有作业ID的代码空间状态"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        
        # 创建测试学生，代码空间状态为running但没有作业ID
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Status", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 获取状态
            status = await CODESPACE.get_status(stu.sid)
            self.assertEqual(status, "stopped")
            LOGGER.info("成功获取状态: %s", status)
            
            # 验证状态已更新
            updated_stu = await TABLE.read(stu.sid)
            self.assertEqual(updated_stu.codespace.status, "stopped")
            LOGGER.info("成功验证状态已更新为stopped")
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_status_running(self):
        """测试获取running状态的代码空间状态"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        from core import DB_STU
        import unittest.mock as mock
        import cluster
        
        # 创建测试学生，代码空间状态为running
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Status", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟作业ID
            job_id = "test_job_789"
            await DB_STU.set(f"{stu.sid}:job_id", job_id)
            LOGGER.info("设置作业ID: %s", job_id)
            
            # 模拟CLUSTER.get_job_status返回RUNNING状态
            with mock.patch('core.CLUSTER.get_job_status', return_value=cluster.ClusterABC.JobStatus.RUNNING):
                # 获取状态
                status = await CODESPACE.get_status(stu.sid)
                self.assertEqual(status, "running")
                LOGGER.info("成功获取running状态: %s", status)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            await DB_STU.delete(f"{stu.sid}:job_id")
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_status_starting(self):
        """测试获取starting状态的代码空间状态"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        from core import DB_STU
        import unittest.mock as mock
        import cluster
        
        # 创建测试学生，代码空间状态为running
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Status", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟作业ID
            job_id = "test_job_789"
            await DB_STU.set(f"{stu.sid}:job_id", job_id)
            LOGGER.info("设置作业ID: %s", job_id)
            
            # 模拟CLUSTER.get_job_status返回PENDING状态
            with mock.patch('core.CLUSTER.get_job_status', return_value=cluster.ClusterABC.JobStatus.PENDING):
                # 获取状态
                status = await CODESPACE.get_status(stu.sid)
                self.assertEqual(status, "starting")
                LOGGER.info("成功获取starting状态: %s", status)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            await DB_STU.delete(f"{stu.sid}:job_id")
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_status_finished(self):
        """测试获取已结束作业的代码空间状态"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        from core import DB_STU
        import unittest.mock as mock
        import cluster
        
        # 创建测试学生，代码空间状态为running
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Status", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟作业ID
            job_id = "test_job_789"
            await DB_STU.set(f"{stu.sid}:job_id", job_id)
            LOGGER.info("设置作业ID: %s", job_id)
            
            # 模拟CLUSTER.get_job_status返回SUCCESS状态
            with mock.patch('core.CLUSTER.get_job_status', return_value=cluster.ClusterABC.JobStatus.SUCCESS):
                # 获取状态
                status = await CODESPACE.get_status(stu.sid)
                self.assertEqual(status, "stopped")
                LOGGER.info("成功获取stopped状态: %s", status)
                
                # 验证状态已更新
                updated_stu = await TABLE.read(stu.sid)
                self.assertEqual(updated_stu.codespace.status, "stopped")
                LOGGER.info("成功验证状态已更新为stopped")
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            await DB_STU.delete(f"{stu.sid}:job_id")
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_status_error(self):
        """测试获取代码空间状态时发生异常"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        from core import DB_STU
        import unittest.mock as mock
        
        # 创建测试学生，代码空间状态为running
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test Status", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="http://example.com",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟作业ID
            job_id = "test_job_789"
            await DB_STU.set(f"{stu.sid}:job_id", job_id)
            LOGGER.info("设置作业ID: %s", job_id)
            
            # 模拟CLUSTER.get_job_status抛出异常
            with mock.patch('core.CLUSTER.get_job_status', side_effect=Exception("模拟的集群错误")):
                # 获取状态
                status = await CODESPACE.get_status(stu.sid)
                self.assertEqual(status, "stopped")
                LOGGER.info("成功获取stopped状态: %s", status)
                
                # 验证状态已更新
                updated_stu = await TABLE.read(stu.sid)
                self.assertEqual(updated_stu.codespace.status, "stopped")
                LOGGER.info("成功验证状态已更新为stopped")
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            await DB_STU.delete(f"{stu.sid}:job_id")
            LOGGER.info("删除测试学生: %s", stu.sid)

    async def test_get_url_not_found(self):
        """测试获取不存在学生的代码空间URL"""
        from core.student import CODESPACE, StudentNotFoundError
        
        # 测试不存在的学生ID
        with self.assertRaises(StudentNotFoundError):
            await CODESPACE.get_url("non_existent_sid")
        LOGGER.info("成功测试: 获取不存在学生的代码空间URL抛出StudentNotFoundError")
    
    async def test_get_url_stopped(self):
        """测试获取stopped状态的代码空间URL"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        import unittest.mock as mock
        
        # 创建测试学生，代码空间状态为stopped
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test URL", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="stopped",  # 已停止状态
                url="",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 使用mock模拟get_status返回"stopped"
            with mock.patch.object(CODESPACE, 'get_status', return_value="stopped"):
                # 获取URL
                url = await CODESPACE.get_url(stu.sid)
                self.assertFalse(url)  # 应该返回False
                LOGGER.info("成功获取stopped状态的URL: %s", url)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_url_starting(self):
        """测试获取starting状态的代码空间URL"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        import unittest.mock as mock
        
        # 创建测试学生
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test URL", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态，但get_status会被模拟返回"starting"
                url="",
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 使用mock模拟get_status返回"starting"
            with mock.patch.object(CODESPACE, 'get_status', return_value="starting"):
                # 获取URL
                url = await CODESPACE.get_url(stu.sid)
                self.assertTrue(url)  # 应该返回True
                LOGGER.info("成功获取starting状态的URL: %s", url)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_url_running_with_url(self):
        """测试获取running状态且有URL的代码空间URL"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        import unittest.mock as mock
        
        # 预设的URL
        test_url = "http://example.com/codespace/test"
        
        # 创建测试学生
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test URL", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url=test_url,  # 预设URL
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 使用mock模拟get_status返回"running"
            with mock.patch.object(CODESPACE, 'get_status', return_value="running"):
                # 获取URL
                url = await CODESPACE.get_url(stu.sid)
                self.assertEqual(url, test_url)  # 应该返回预设的URL
                LOGGER.info("成功获取running状态有URL的代码空间URL: %s", url)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_url_running_no_url(self):
        """测试获取running状态但没有URL的代码空间URL"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        from core import DB_STU
        import unittest.mock as mock
        
        # 创建测试学生
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test URL", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="",  # 没有预设URL
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 模拟作业ID
            job_id = "test_job_url"
            await DB_STU.set(f"{stu.sid}:job_id", job_id)
            LOGGER.info("设置作业ID: %s", job_id)
            
            # 使用mock模拟get_status返回"running"
            with mock.patch.object(CODESPACE, 'get_status', return_value="running"):
                # 获取URL
                url = await CODESPACE.get_url(stu.sid)
                self.assertTrue(isinstance(url, str))  # 应该返回生成的URL字符串
                self.assertTrue(len(url) > 0)  # URL不应为空
                LOGGER.info("成功获取running状态无URL的代码空间URL: %s", url)
                
                # 验证URL已被保存到数据库
                updated_stu = await TABLE.read(stu.sid)
                self.assertEqual(updated_stu.codespace.url, url)
                LOGGER.info("成功验证URL已保存到数据库: %s", updated_stu.codespace.url)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            await DB_STU.delete(f"{stu.sid}:job_id")
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_url_running_no_job_id(self):
        """测试获取running状态但没有作业ID的代码空间URL"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        import unittest.mock as mock
        
        # 创建测试学生
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test URL", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="running",  # 运行状态
                url="",  # 没有预设URL
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 使用mock模拟get_status返回"running"
            with mock.patch.object(CODESPACE, 'get_status', return_value="running"):
                # 获取URL，由于没有作业ID，应该返回False
                url = await CODESPACE.get_url(stu.sid)
                self.assertFalse(url)  # 应该返回False
                LOGGER.info("成功获取running状态无作业ID的代码空间URL: %s", url)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
    
    async def test_get_url_unknown_status(self):
        """测试获取未知状态的代码空间URL"""
        from core.student import TABLE, Student, UserInfo, CodespaceInfo, CODESPACE
        import unittest.mock as mock
        
        # 创建测试学生
        stu = Student(
            sid=self.test_id,
            pwd_hash="test_hash",
            user_info=UserInfo(name="Test URL", mail="test@example.com"),
            codespace=CodespaceInfo(
                status="unknown",  # 未知状态
            ),
        )
        
        try:
            # 创建学生记录
            self.assertTrue(await TABLE.create(stu))
            LOGGER.info("创建测试学生: %s", stu.sid)
            
            # 使用mock模拟get_status返回"unknown"
            with mock.patch.object(CODESPACE, 'get_status', return_value="unknown"):
                # 获取URL
                url = await CODESPACE.get_url(stu.sid)
                self.assertFalse(url)  # 应该返回False
                LOGGER.info("成功获取未知状态的代码空间URL: %s", url)
            
        finally:
            # 清理测试数据
            await TABLE.delete(stu.sid)
            LOGGER.info("删除测试学生: %s", stu.sid)
