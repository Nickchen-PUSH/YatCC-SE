import unittest

import svc_adm
from base.logger import logger
from core import student, admin
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
        async def ado():
            # 创建学生
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

            stu = student.Student(
                sid="24111353",
                user_info={
                    "name": "顾宇浩clone1",
                    "mail": "yhgu2001@outlook.com",
                },
                codespace={
                    "time_quota": 3600,
                },
            )
            stu.reset_password("1234567")
            await student.TABLE.create(stu)
            await student.CODESPACE.start("24111353")

            stu = student.Student(
                sid="24111354",
                user_info={
                    "name": "顾宇浩clone2",
                    "mail": "yhgu2002@outlook.com",
                },
                codespace={
                    "time_quota": 3600,
                    "time_used": 3600,
                },
            )
            stu.reset_password("12345678")
            await student.TABLE.create(stu)
            # 设置管理员APIKEY
            await admin.API_KEY.set("123456")

        RUNNER.run(ado())

    @classmethod
    def tearDownClass(cls) -> None:
        async def ado():
            await student.TABLE.delete("24111352")
            await student.TABLE.delete("24111353")
            await student.TABLE.delete("24111354")

        RUNNER.run(ado())

    def setUp(self) -> None:
        global WSGI
        self.client = WSGI.test_client()
        self.header = {"ADM-API-KEY": {"123456"}}
        self.wrong_header = {"ADM-API-KEY": {"wrong_key"}}

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

    def test_student_info(self):

        self._test_api_key("/student/24111352", None, "GET")
        # 测试含有apikey获取学生信息
        resp = self.client.get("/student/24111352", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json["id"], "24111352")
        self.assertEqual(resp.json["name"], "顾宇浩")
        self.assertEqual(resp.json["mail"], "yhgu2000@outlook.com")
        # 测试获取不存在的学生信息
        resp = self.client.get("/student/404", headers=self.header)
        self.assertEqual(resp.status_code, 404)

    def test_student_list(self):
        self._test_api_key("/student", None, "GET")
        # 测试含有apikey获取学生列表
        resp = self.client.get("/student", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json[0]["id"], "24111352")
        self.assertEqual(resp.json[0]["name"], "顾宇浩")
        self.assertEqual(resp.json[0]["mail"], "yhgu2000@outlook.com")
        self.assertEqual(resp.json[1]["id"], "24111353")
        self.assertEqual(resp.json[1]["name"], "顾宇浩clone1")
        self.assertEqual(resp.json[1]["mail"], "yhgu2001@outlook.com")
        self.assertEqual(resp.json[2]["id"], "24111354")
        self.assertEqual(resp.json[2]["name"], "顾宇浩clone2")
        self.assertEqual(resp.json[2]["mail"], "yhgu2002@outlook.com")

    def test_create_student(self):

        students = [
            {
                "id": "24111355",
                "name": "顾宇浩clone3",
                "mail": "yhgu2003@outlook.com",
                "time_quota": 3600,
                "pwd": "12345678",
            },
            {
                "id": "24111356",
                "name": "顾宇浩clone4",
                "mail": "yhgu2004@outlook.com",
                "time_quota": 3600,
                "pwd": "12345678",
            },
        ]

        self._test_api_key("/student", students, "POST")

        # 测试含有apikey创建学生
        resp = self.client.post(
            "/student",
            json=students,
            headers=self.header,
        )
        self.assertEqual(resp.status_code, 200)

        # 检测创建学生是否正确
        resp = self.client.get("/student/24111355", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json["id"], "24111355")
        self.assertEqual(resp.json["name"], "顾宇浩clone3")
        self.assertEqual(resp.json["mail"], "yhgu2003@outlook.com")

        resp = self.client.get("/student/24111356", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json["id"], "24111356")
        self.assertEqual(resp.json["name"], "顾宇浩clone4")
        self.assertEqual(resp.json["mail"], "yhgu2004@outlook.com")

        async def ado():
            # 删除测试数据
            await student.TABLE.delete("24111355")
            await student.TABLE.delete("24111356")

        RUNNER.run(ado())

    def test_delete_student(self):

        delete_students = [
            {
                "sid": "24111352",
            },
            {
                "sid": "24111353",
            },
        ]

        self._test_api_key("/student", delete_students, "DELETE")

        # 测试含有apikey删除学生
        resp = self.client.delete(
            "/student",
            json=delete_students,
            headers=self.header,
        )
        self.assertEqual(resp.status_code, 200)

        # 检测删除学生是否正确
        resp = self.client.get("/student/24111352", headers=self.header)
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get("/student/24111353", headers=self.header)
        self.assertEqual(resp.status_code, 404)

        resp = self.client.get("/student/24111354", headers=self.header)
        self.assertEqual(resp.status_code, 200)

        async def ado():
            # 重置测试数据
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

            stu = student.Student(
                sid="24111353",
                user_info={
                    "name": "顾宇浩clone1",
                    "mail": "yhgu2001@outlook.com",
                },
                codespace={
                    "time_quota": 3600,
                },
            )
            stu.reset_password("1234567")
            await student.TABLE.create(stu)

        RUNNER.run(ado())

    def test_codespace(self):
        self._test_api_key("/student/codespace/24111352", None, "GET")

        # 测试获取学生代码空间
        resp = self.client.get("/student/codespace/24111352", headers=self.header)
        self.assertEqual(resp.status_code, 303)

        # 测试获取运行中的学生代码空间
        resp = self.client.get("/student/codespace/24111353", headers=self.header)
        self.assertEqual(resp.status_code, 302)

        # 测试获取不存在的学生代码空间
        resp = self.client.get("/student/codespace/404", headers=self.header)
        self.assertEqual(resp.status_code, 404)

    def test_start_codespace(self):
        self._test_api_key("/student/codespace/24111352", None, "POST")

        # 测试启动学生代码空间
        resp = self.client.post("/student/codespace/24111352", headers=self.header)
        self.assertEqual(resp.status_code, 200)

        # 测试启动已启动的学生代码空间
        resp = self.client.post("/student/codespace/24111353", headers=self.header)
        self.assertEqual(resp.status_code, 202)

        # 测试启动达到限制的学生代码空间
        resp = self.client.post("/student/codespace/24111354", headers=self.header)
        self.assertEqual(resp.status_code, 402)

        # 测试启动的学生代码空间
        resp = self.client.post("/student/codespace/404", headers=self.header)
        self.assertEqual(resp.status_code, 404)

        async def ado():
            # 重置测试数据
            await student.CODESPACE.stop("24111352")

        RUNNER.run(ado())

    def test_stop_codespace(self):
        self._test_api_key("/student/codespace/24111352", None, "DELETE")

        # 测试停止已停止的学生代码空间
        resp = self.client.delete("/student/codespace/24111352", headers=self.header)
        self.assertEqual(resp.status_code, 202)

        # 测试停止学生代码空间
        resp = self.client.delete("/student/codespace/24111353", headers=self.header)
        self.assertEqual(resp.status_code, 200)

        # 测试停止不存在的学生代码空间
        resp = self.client.delete("/student/codespace/404", headers=self.header)
        self.assertEqual(resp.status_code, 404)

        async def ado():
            # 重置测试数据
            await student.CODESPACE.start("24111353")

        RUNNER.run(ado())

    def test_codespace_info(self):
        self._test_api_key("/student/codespace/info/24111352", None, "GET")

        # 测试获取停止中的学生代码空间信息
        resp = self.client.get("/student/codespace/info/24111352", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json["status"], "stopped")

        # 测试获取运行中的学生代码空间信息
        resp = self.client.get("/student/codespace/info/24111353", headers=self.header)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json["status"], "running")

        # 测试获取不存在的学生代码空间信息
        resp = self.client.get("/student/codespace/info404", headers=self.header)
        self.assertEqual(resp.status_code, 404)

    def test_batch_start_codespace(self):
        ids = [
            "24111352",
            "24111353",
            "24111354",
        ]
        self._test_api_key("/student/codespace", {"ids": ids}, "POST")

        # 测试批量启动学生代码空间
        resp = self.client.post(
            "/student/codespace", json={"ids": ids}, headers=self.header
        )
        self.assertEqual(resp.status_code, 200)

        self.assertIn("24111352", resp.json["success"])
        self.assertNotIn("24111353", resp.json["success"])
        self.assertNotIn("24111354", resp.json["success"])

        async def ado():
            # 恢复旧数据
            await student.CODESPACE.stop("24111352")

        RUNNER.run(ado())

    def test_batch_stop_codespace(self):
        ids = [
            "24111352",
            "24111353",
        ]
        self._test_api_key("/student/codespace", {"ids": ids}, "DELETE")

        # 测试批量停止学生代码空间
        resp = self.client.delete(
            "/student/codespace", json={"ids": ids}, headers=self.header
        )
        self.assertEqual(resp.status_code, 200)

        self.assertIn("24111353", resp.json["success"])
        self.assertNotIn("24111352", resp.json["success"])

        async def ado():
            # 恢复旧数据
            await student.CODESPACE.start("24111353")

        RUNNER.run(ado())

    def test_update_codespace_quota(self):
        self._test_api_key(
            "/student/codespace/quota/24111352", {"time_quota": 7200}, "PUT"
        )

        # 测试更新学生代码空间配额
        resp = self.client.put(
            "/student/codespace/quota/24111352",
            json={
                "time_quota": 7200,
                "space_quota": 1024 * 1024 * 1024,
            },
            headers=self.header,
        )
        self.assertEqual(resp.status_code, 200)

        # 检查更新是否成功
        resp = self.client.get("/student/24111352", headers=self.header)
        self.assertEqual(resp.json["time_quota"], 7200)
