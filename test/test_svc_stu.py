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
        from util import api_key_enc
        global WSGI
        self.client = WSGI.test_client()
        self.header = {"X-API-KEY": {api_key_enc("24111352")}}
        self.wrong_header = {"X-API-KEY": {api_key_enc("wrong_sid")}}

    def tearDown(self) -> None:
        return

    def _test_api_key(self, url, json, method):
        n_resp = None
        w_resp = None
        match method:
            case "GET":
                n_resp = self.client.get(url)
                w_resp = self.client.get(url, headers=self.wrong_header)
            case "POST":
                n_resp = self.client.post(url, json=json)
                w_resp = self.client.post(url, json=json, headers=self.wrong_header)
            case "PUT":
                n_resp = self.client.put(url, json=json)
                w_resp = self.client.put(url, json=json, headers=self.wrong_header)
            case "DELETE":
                n_resp = self.client.delete(url, json=json)
                w_resp = self.client.delete(url, json=json, headers=self.wrong_header)
            case "PATCH":
                n_resp = self.client.patch(url, json=json)
                w_resp = self.client.patch(url, json=json, headers=self.wrong_header)


        self.assertEqual(n_resp.status_code, 401)
        self.assertEqual(w_resp.status_code, 403)

    def test_login(self):
        # 测试使用正确密码登录
        resp = self.client.post(
            "/login",
            json={
                "sid": "24111352",
                "pwd": "123456",
            },
        )
        self.assertEqual(resp.status_code, 200)
        
        # 测试使用错误密码登录
        resp = self.client.post(
            "/login",
            json={
                "sid": "24111352",
                "pwd": "wrong_password",
            },
        )
        self.assertEqual(resp.status_code, 401)

    def test_uesr_info(self):
        
        self._test_api_key("/user", None, "GET")
        # 测试含有apikey获取用户信息
        resp = self.client.get("/user", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        # 检测获取用户信息是否正确
        user_info = resp.json
        self.assertEqual(user_info["name"], "顾宇浩")
        self.assertEqual(user_info["mail"], "yhgu2000@outlook.com")

        new_user_info = {
            "name": "王文博",
            "mail": "wwb2000@outlook.com",
        }

        self._test_api_key("/user", new_user_info, "PUT")

        # 测试含有apikey更新用户信息
        resp = self.client.put(
            "/user",
            json=new_user_info,
            headers=self.header,
        )

        self.assertEqual(resp.status_code, 200)

        # 检测用户信息是否被更改
        resp = self.client.get("/user", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        
        updated_info = resp.json
        self.assertEqual(updated_info["name"], new_user_info["name"])
        self.assertEqual(updated_info["mail"], new_user_info["mail"])

        # 恢复旧数据
        resp = self.client.put(
            "/user",
            json={
                    "name": "顾宇浩",
                    "mail": "yhgu2000@outlook.com",
            },
            headers=self.header,
        )

        self.assertEqual(resp.status_code, 200)

        

    def test_reset_password(self):

        reset_pwd = {
            "old_pwd": "123456",
            "new_pwd": "12345678",
        }

        self._test_api_key("/user", reset_pwd, "PATCH")
        # 测试含有apikey重置密码
        resp = self.client.patch(
            "/user",
            json=reset_pwd,
            headers=self.header,
        )
        self.assertEqual(resp.status_code, 200)

        # 测试使用新密码登录
        resp = self.client.post(
            "/login",
            json={
                "sid": "24111352",
                "pwd": "12345678",
            },
        )
        self.assertEqual(resp.status_code, 200)

        # 测试使用旧密码登录
        resp = self.client.post(
            "/login",
            json={
                "sid": "24111352",
                "pwd": "123456",
            },
        )
        self.assertEqual(resp.status_code, 401)

        # 测试使用错误旧密码
        resp = self.client.patch(
            "/user",
            json={
                "old_pwd": "wrong",
                "new_pwd": "12345678",
            },
            headers=self.header,
        )

        self.assertEqual(resp.status_code, 400)

        # 恢复旧数据
        resp = self.client.patch(
            "/user",
            json={
                "old_pwd": "12345678",
                "new_pwd": "123456",
            },
            headers=self.header,
        )

        self.assertEqual(resp.status_code, 200)