import unittest

import svc_adm
from base.logger import logger
from core import student
from base import RUNNER

LOGGER = logger(__spec__, __file__)
WSGI: svc_adm.AsyncFlask


def setUpModule() -> None:
    global WSGI
    from . import setup_test
    from . import ainit_core

    setup_test(__name__)
    RUNNER.run(ainit_core())
    LOGGER.dir.mkdir(parents=True, exist_ok=True)
    WSGI = svc_adm.wsgi()


def tearDownModule() -> None:
    return

class Basic(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        return

    @classmethod
    def tearDownClass(cls) -> None:
        return

    def setUp(self) -> None:
        global WSGI
        self.client = WSGI.test_client()

    def tearDown(self) -> None:
        return
    
    # 在这里添加测试方法