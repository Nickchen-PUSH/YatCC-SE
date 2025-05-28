import unittest

import svc_stu
from base.logger import logger
from core import student
from . import RUNNER

LOGGER = logger(__spec__, __file__)
WSGI: svc_stu.AsyncFlask


def setUpModule() -> None:
    global WSGI
    from . import setup_test
    from . import ainit_core

    setup_test(__name__)
    RUNNER.run(ainit_core())
    LOGGER.dir.mkdir(parents=True, exist_ok=True)
    WSGI = svc_stu.wsgi()


def tearDownModule() -> None:
    return


class Basic(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        async def ado():
            stu = student.Student(
                sid="24111352",
                user_info={
                    "name": "顾宇浩",
                    "mail": "yhgu2000@outlook.com",
                },
                codespace={
                    "time_quota": 3600,
                },
            )
            stu.reset_password("123456")
            await student.TABLE.create(stu)

        RUNNER.run(ado())

    @classmethod
    def tearDownClass(cls) -> None:
        async def ado():
            await student.TABLE.delete("24111352")

        RUNNER.run(ado())

    def setUp(self) -> None:
        global WSGI
        self.client = WSGI.test_client()

    def tearDown(self) -> None:
        return

    def test_login(self):
        resp = self.client.post(
            "/login",
            json={
                "sid": "24111352",
                "pwd": "123456",
            },
        )
        self.assertEqual(resp.status_code, 200)
        
        resp = self.client.post(
            "/login",
            json={
                "sid": "24111352",
                "pwd": "wrong_password",
            },
        )
        self.assertEqual(resp.status_code, 401)
