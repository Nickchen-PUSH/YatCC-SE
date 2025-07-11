import asyncio as aio
from uuid import uuid4

from flask import Response, g, redirect, request
from flask_openapi3 import Info, OpenAPI, Tag
from pydantic import BaseModel, Field, RootModel

from config import CONFIG, ENVIRON
from base.logger import logger
from base import RUNNER
from core import admin, student

LOGGER = logger(__spec__, __file__)


class AsyncFlask(OpenAPI):

    def async_to_sync(self, func):
        import contextvars

        def wrapper(*args, **kwargs):
            return context.run(loop.run_until_complete, func(*args, **kwargs))

        context = contextvars.copy_context()
        loop = RUNNER.get_loop()
        return wrapper


WSGI = AsyncFlask(
    __name__,
    info=Info(title="管理员服务", version="0.2.0"),
    security_schemes={
        "api-key-in-query": {
            "type": "apiKey",
            "name": "ADM-API-KEY",
            "in": "query",
        },
        "api-key-in-header": {
            "type": "apiKey",
            "name": "ADM-API-KEY",
            "in": "header",
        },
        "api-key-in-cookie": {
            "type": "apiKey",
            "name": "ADM-API-KEY",
            "in": "cookie",
        },
    },
    static_folder=CONFIG.SVC_ADM.static_dir,
    static_url_path="/static",
)

_SECURITY = [
    {"api-key-in-query": []},
    {"api-key-in-header": []},
    {"api-key-in-cookie": []},
]
_OK = Response(status=200)


class ErrorResponse(Exception):
    def __init__(self, res: Response):
        self.res = res


WSGI.register_error_handler(ErrorResponse, lambda e: e.res)


async def check_api_key():
    """检查管理员 API-KEY 是否正确"""
    api_key = request.headers.get("ADM-API-KEY")
    if api_key is None:
        api_key = request.cookies.get("ADM-API-KEY")
    if api_key is None:
        api_key = request.args.get("ADM-API-KEY")

    if api_key is None:
        raise ErrorResponse(
            Response(
                "UNAUTHORIZED: please set the 'ADM-API-KEY'"
                " in headers, cookies or query parameters.",
                status=401,
            )
        )

    if not api_key == await admin.API_KEY.get():
        raise ErrorResponse(
            Response(
                "FORBIDDEN: incorrect API-KEY",
                status=403,
            )
        )



_CHECK_API_KEY_RESPONSES = {
    401: {"description": "未授权，没有提供 API-KEY"},
    403: {"description": "API-KEY 无效"},
}


# ==================================================================================== #
_TAG_STUDENT = Tag(name="student", description="学生管理")


class StudentBrief(BaseModel):
    id: str = student.Student.model_fields["sid"]
    name: str = student.UserInfo.model_fields["name"]
    mail: str = student.UserInfo.model_fields["mail"]

    @staticmethod
    def from_student(stu: student.Student) -> "StudentBrief":
        return StudentBrief(
            id=stu.sid,
            name=stu.user_info.name,
            mail=stu.user_info.mail,
        )


class StudentDetail(StudentBrief):
    status: str = student.CodespaceInfo.model_fields["status"]
    url: str = student.CodespaceInfo.model_fields["url"]
    time_quota: float = student.CodespaceInfo.model_fields["time_quota"]
    time_used: float = student.CodespaceInfo.model_fields["time_used"]
    last_start: float = student.CodespaceInfo.model_fields["last_start"]
    last_stop: float = student.CodespaceInfo.model_fields["last_stop"]
    last_active: float = student.CodespaceInfo.model_fields["last_active"]
    last_watch: float = student.CodespaceInfo.model_fields["last_watch"]

    @staticmethod
    def from_student(stu: student.Student) -> "StudentDetail":
        return StudentDetail(
            id=stu.sid,
            name=stu.user_info.name,
            mail=stu.user_info.mail,
            status=stu.codespace.status,
            url=stu.codespace.url,
            time_quota=stu.codespace.time_quota,
            time_used=stu.codespace.time_used,
            last_start=stu.codespace.last_start,
            last_stop=stu.codespace.last_stop,
            last_active=stu.codespace.last_active,
            last_watch=stu.codespace.last_watch,
        )

class DetailPath(BaseModel):
    sid: str = student.Student.model_fields["sid"]
@WSGI.get(
    "/student/<sid>",
    tags=[_TAG_STUDENT],
    responses={
        200: {
            "description": "成功，返回学生信息",
            "content": {
                "application/json": {"schema": StudentDetail.model_json_schema()}
            },
        },
        404: {"description": "学生不存在"},
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def student_detail(path: DetailPath):
    """获取学生详细信息"""
    await check_api_key()
    try:
        student_data = await student.TABLE.read(path.sid)
    except student.StudentNotFoundError:
        raise ErrorResponse(Response("Student not found", status=404))
    return StudentDetail.from_student(student_data).model_dump(), 200


@WSGI.get(
    "/student",
    tags=[_TAG_STUDENT],
    responses={
        200: {
            "description": "成功，返回学生列表",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": StudentBrief.model_json_schema(),
                    }
                }
            },
        },
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def student_list():
    """获取学生列表"""
    await check_api_key()
    students = [
        StudentBrief.from_student(stu).model_dump()
        async for stu in student.TABLE.iter_all()
    ]
    
    return students, 200


class StudentCreate(StudentBrief):
    pwd: str = Field(..., description="密码")
    time_quota: int = Field(0, description="时间配额，单位为秒")


@WSGI.post(
    "/student",
    tags=[_TAG_STUDENT],
    responses={
        200: {
            "description": "批量创建学生结果",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {
                                "type": "array",
                                "items": StudentBrief.model_json_schema(),
                            },
                            "failed": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "reason": {"type": "string"},
                                    },
                                },
                            },
                        },
                    }
                }
            },
        },
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def create_student(body: RootModel[list[StudentCreate]]):
    """创建学生"""
    await check_api_key()
    success = []
    failed = []
    for stu_data in body.root:
        try:
            stu = student.Student(
                sid=stu_data.id,
                user_info=student.UserInfo(name=stu_data.name, mail=stu_data.mail),
                codespace=student.CodespaceInfo(time_quota=stu_data.time_quota),
            )
            stu.reset_password(stu_data.pwd)
            await student.TABLE.create(stu)
            success.append(StudentBrief.from_student(stu).model_dump())
        except Exception as e:
            failed.append({"id": stu.sid, "reason": str(e)})
    return {
        "success": success,
        "failed": failed,
    }


# 批量删除学生API
class StudentDelete(BaseModel):
    sid: str = Field(..., description="学生ID")


@WSGI.delete(
    "/student",
    tags=[_TAG_STUDENT],
    responses={
        200: {
            "description": "批量删除学生结果",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "failed": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "reason": {"type": "string"},
                                    },
                                },
                            },
                        },
                    }
                }
            },
        },
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def batch_delete_student(body: RootModel[list[StudentDelete]]):
    """批量删除学生"""
    await check_api_key()
    success = []
    failed = []
    for stu_data in body.root:
        try:
            await student.TABLE.delete(stu_data.sid)
            success.append(stu_data.sid)
        except Exception as e:
            failed.append({"id": stu_data.sid, "reason": str(e)})
    return {
        "success": success,
        "failed": failed,
    }


# ==================================================================================== #


# 进入学生代码空间 api
@WSGI.get(
    "/student/codespace/<sid>",
    tags=[_TAG_STUDENT],
    responses={
        302: {"description": "容器正在运行，重定向到学生代码空间页面"},
        303: {"description": "容器不在运行，重定向到代码空间管理页面"},
        307: {"description": "容器正在运行，但代码空间未启动"},
        404: {"description": "学生不存在"},
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def student_codespace(path: DetailPath):
    """进入学生代码空间（重定向）"""
    await check_api_key()
    try:
        # 检查学生是否存在
        student_data = await student.TABLE.read(path.sid)
        
        # 获取代码空间状态和URL
        status = await student.CODESPACE.get_status(path.sid)
        url = await student.CODESPACE.get_url(path.sid)
        
        if status == "running" and url:
            # 代码空间正在运行且有URL，重定向到代码空间
            return redirect(url, code=302)
        elif status == "starting" or url is True:
            # 代码空间正在启动中，重定向到管理页面
            return redirect(f"/student/codespace/manage/{path.sid}", code=307)
        else:
            # 其他情况重定向到管理页面
            return redirect(f"/student/codespace/manage/{path.sid}", code=303)
            
    except student.StudentNotFoundError:
        raise ErrorResponse(Response("Student not found", status=404))


# 开启学生代码空间 api
@WSGI.post(
    "/student/codespace/<sid>",
    tags=[_TAG_STUDENT],
    responses={
        200: {"description": "启动操作成功"},
        202: {"description": "代码空间正在或已经启动"},
        404: {"description": "学生不存在"},
        402: {"description": "代码空间配额已耗尽"},
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def student_codespace_start(path: DetailPath):
    """启动学生代码空间，立即返回，不会等待代码空间启动完成"""
    await check_api_key()
    try:
        status=await student.CODESPACE.get_status(path.sid)
        if status=="running":
            return Response("代码空间已启动", status=202)
    except student.StudentNotFoundError:
        return Response("Student not found", status=404)
    try:
        await student.CODESPACE.start(path.sid)
        return _OK
    except student.CodespaceQuotaExceededError:
        return Response("代码空间配额已耗尽", status=402)
    



# 关闭学生代码空间 api
@WSGI.delete(
    "/student/codespace/<sid>",
    tags=[_TAG_STUDENT],
    responses={
        200: {"description": "停止操作成功"},
        202: {"description": "代码空间不在运行"},
        404: {"description": "学生不存在"},
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def student_codespace_stop(path: DetailPath):
    """停止学生代码空间，立即返回，不会等待代码空间停止完成"""
    await check_api_key()
    try:
        status=await student.CODESPACE.get_status(path.sid)
        if status=="stopped":
            return Response("代码空间不在运行", status=202)
    except student.StudentNotFoundError:
        return Response("学生不存在", status=404)
    await student.CODESPACE.stop(path.sid)
    return _OK


# 获取学生代码空间信息 api
@WSGI.get(
    "/student/codespace/info/<sid>",
    tags=[_TAG_STUDENT],
    responses={
        200: {
            "description": "成功返回学生代码空间信息",
            "content": {
                "application/json": {
                    "schema": student.CodespaceInfo.model_json_schema()
                }
            },
        },
        404: {"description": "学生不存在"},
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def student_codespace_info(path: DetailPath):
    """获取学生代码空间信息"""
    await check_api_key()
    try:
        student_data=await student.TABLE.read(path.sid)
        return StudentDetail.from_student(student_data).model_dump(),200
    except student.StudentNotFoundError:
        return Response("学生不存在", status=404)


# 保持学生代码空间活跃 api
@WSGI.post(
    "/student/keepalive/<sid>",
    tags=[_TAG_STUDENT],
    responses={
        200: {"description": "保持活跃操作成功"},
        202: {"description": "代码空间不在运行"},
        404: {"description": "学生不存在"},
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def student_codespace_keepalive(path: DetailPath):
    """保持学生代码空间活跃，防止超时"""
    pass


# 定义批量操作请求模型
class CodespaceBatchOperation(BaseModel):
    ids: list[str] = Field(..., description="学生ID列表")


# 批量启动代码空间API
@WSGI.post(
    "/student/codespace",
    tags=[_TAG_STUDENT],
    responses={
        200: {
            "description": "批量启动代码空间结果",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "array", "items": {"type": "string"}},
                            "failed": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "reason": {"type": "string"},
                                    },
                                },
                            },
                        },
                    }
                }
            },
        },
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def batch_start_codespace(body: CodespaceBatchOperation):
    """批量启动多个学生的代码空间"""
    await check_api_key()
    success = []
    failed = []
    for sid in body.ids:
        try:
            status = await student.CODESPACE.get_status(sid)
            if status == "running":
                failed.append({"id": sid, "reason": "代码空间已在运行"})
                continue
            await student.CODESPACE.start(sid)
            success.append(sid)
        except student.StudentNotFoundError:
            failed.append({"id": sid, "reason": "学生不存在"})
        except student.CodespaceQuotaExceededError:
            failed.append({"id": sid, "reason": "代码空间配额已耗尽"})
    return {
        "success": success,
        "failed": failed,
    }, 200


# 批量停止代码空间API
@WSGI.delete(
    "/student/codespace",
    tags=[_TAG_STUDENT],
    responses={
        200: {
            "description": "批量停止代码空间结果",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "array", "items": {"type": "string"}},
                            "failed": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string"},
                                        "reason": {"type": "string"},
                                    },
                                },
                            },
                        },
                    }
                }
            },
        },
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def batch_stop_codespace(body: CodespaceBatchOperation):
    """批量停止多个学生的代码空间"""
    await check_api_key()
    success = []
    failed = []
    for sid in body.ids:
        try:
            status = await student.CODESPACE.get_status(sid)
            if status == "stopped":
                failed.append({"id": sid, "reason": "代码空间不在运行"})
                continue
            await student.CODESPACE.stop(sid)
            success.append(sid)
        except student.StudentNotFoundError:
            failed.append({"id": sid, "reason": "学生不存在"})
    return {
        "success": success,
        "failed": failed,
    }, 200


# 调整学生代码空间配额API
class CodespaceQuota(BaseModel):
    time_quota: int = Field(..., description="时间配额（秒）")
    space_quota: int = Field(0, description="空间配额（字节）")


@WSGI.put(
    "/student/codespace/quota/<sid>",
    tags=[_TAG_STUDENT],
    responses={
        200: {"description": "配额调整成功"},
        404: {"description": "学生不存在"},
        **_CHECK_API_KEY_RESPONSES,
    },
)
async def update_student_codespace_quota(path: DetailPath, body: CodespaceQuota):
    """调整学生代码空间配额"""
    await check_api_key()
    try:
        # 检查学生是否存在
        student_data = await student.TABLE.read(path.sid)
        # 暂时不支持空间配额调整
        student_data.codespace.time_quota = body.time_quota
        await student.TABLE.write(student_data)
        return _OK
    except student.StudentNotFoundError:
        return Response("学生不存在", status=404)


# ==================================================================================== #

@WSGI.route("/")
@WSGI.route('/<path:path>')
def index(path=None):
    return redirect("/static/index.html")

def wsgi():
    import base.logger as logger
    from core import ainit

    logger.setup_logger(
        log_dir=CONFIG.log_dir,
        index_name="svc_adm",
    )
    LOGGER.info("Initializing admin service...")
    RUNNER.run(ainit(cluster_mock=ENVIRON.mock_cluster))
    return WSGI


if __name__ == "__main__":
    from argparse import ArgumentParser

    argp = ArgumentParser()
    argp.add_argument("--nodbg", action="store_true")
    argp.add_argument("--port", type=int, default=5001)

    args = argp.parse_args()
    ARG_NODBG: bool = args.nodbg
    ARG_PORT: int = args.port

    wsgi().run(debug=not ARG_NODBG, port=ARG_PORT)
