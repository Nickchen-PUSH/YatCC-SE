import core
from base.logger import logger

from .. import RUNNER, AsyncTestCase

LOGGER = logger(__spec__, __file__)


def setUpModule() -> None:
    from .. import setup_test, ainit_core

    setup_test(__name__)
    RUNNER.run(ainit_core())


def tearDownModule() -> None:
    return


class InitTest(AsyncTestCase):
    """测试核心层初始化"""

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

    def test_init(self):
        """测试核心层初始化"""

        self.assertTrue(core.DB0.ping())
        self.assertTrue(core.DB_STU.ping())
        self.assertTrue(core.CLUSTER.ready())


if __name__ == "__main__":
    import unittest

    unittest.main()
