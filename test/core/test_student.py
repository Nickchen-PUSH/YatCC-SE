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
