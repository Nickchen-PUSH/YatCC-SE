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

            stu = student.Student(
                sid="24111354",
                user_info={
                    "name": "顾宇浩clone2",
                    "mail": "yhgu2002@outlook.com",
                },
                codespace={
                    "time_quota": 3600,
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
        self.header = {"X-API-KEY": {"123456"}}
        self.wrong_header = {"X-API-KEY": {"wrong_key"}}

    def tearDown(self) -> None:
        return
    
    def test_student_info(self):
        # 测试不含有apikey获取学生信息
        resp = self.client.get("/student/24111352")
        self.assertEqual(resp.status_code, 401)
        # 测试含有错误的apikey获取学生信息
        resp = self.client.get("/student/24111352", headers=self.wrong_header)
        self.assertEqual(resp.status_code, 403)
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
        # 测试不含有apikey获取学生列表
        resp = self.client.get("/student")
        self.assertEqual(resp.status_code, 401)
        # 测试含有错误的apikey获取学生列表
        resp = self.client.get("/student", headers=self.wrong_header)
        self.assertEqual(resp.status_code, 403)
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
                "sid": "24111355",
                "user_info": {
                    "name": "顾宇浩clone3",
                    "mail": "yhgu2003@outlook.com",
                },
                "codespace": {
                    "time_quota": 3600,
                },
                "pwd": "12345678",
            },
            {
                "sid": "24111356",
                "user_info": {
                    "name": "顾宇浩clone4",
                    "mail": "yhgu2004@outlook.com",
                },
                "codespace": {
                    "time_quota": 3600,
                },
                "pwd": "12345678",
            },
        ]

        # 测试不含有apikey创建学生
        resp = self.client.post(
            "/student",
            json=students,
        )
        self.assertEqual(resp.status_code, 401)

        # 测试含有错误的apikey创建学生
        resp = self.client.post(
            "/student",
            json=students,
            headers=self.wrong_header,
        )
        self.assertEqual(resp.status_code, 403)

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


    def test_delete_student(self):

        delete_students = [
            {
                "sid": "24111352",
            },
            {
                "sid": "24111353",
            },
        ]
        # 测试不含有apikey删除学生
        resp = self.client.delete(
            "/student",
            json=delete_students,
        )
        self.assertEqual(resp.status_code, 401)

        # 测试含有错误的apikey删除学生
        resp = self.client.delete(
            "/student",
            json=delete_students,
            headers=self.wrong_header,
        )
        self.assertEqual(resp.status_code, 403)

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



