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
