import asyncio as aio
from uuid import uuid4

from flask import Response, g, redirect, request
from flask_openapi3 import Info, OpenAPI, Tag
from pydantic import BaseModel, Field

import core.student
from config import CONFIG, ENVIRON
from base.logger import logger
from base import RUNNER

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
    info=Info(title="学生服务", version="0.2.0"),
    security_schemes={
        "api-key-in-query": {
            "type": "apiKey",
            "name": "X-API-KEY",
            "in": "query",
        },
        "api-key-in-header": {
            "type": "apiKey",
            "name": "X-API-KEY",
            "in": "header",
        },
        "api-key-in-cookie": {
            "type": "apiKey",
            "name": "X-API-KEY",
            "in": "cookie",
        },
    },
    static_folder=CONFIG.SVC_STU.static_dir,
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


def _log_exception(e: Exception) -> str:
    uuid = uuid4()
    LOGGER.error("%s - %s\n", uuid, g.get("current_account"), exc_info=e)
    return f"{type(e).__name__}<{uuid}>: {e}"


def _handle_403(e: core.student.StudentNotFoundError) -> Response:
    return Response(_log_exception(e), status=403)


def _handle_exception(e: Exception) -> Response:
    return Response(_log_exception(e), status=500)


WSGI.register_error_handler(ErrorResponse, lambda e: e.res)
WSGI.register_error_handler(core.student.StudentNotFoundError, _handle_403)
WSGI.register_error_handler(Exception, _handle_exception)


@WSGI.route("/")
def index():
    return redirect("/static/index.html")


# ==================================================================================== #
_TAG_LOGIN = Tag(name="login", description="登录认证")


async def check_api_key() -> str:
    """检查 API-KEY，返回账户"""

    from util import api_key_dec

    api_key = request.headers.get("X-API-KEY")
    if api_key is None:
        api_key = request.cookies.get("X-API-KEY")
    if api_key is None:
        api_key = request.args.get("X-API-KEY")
    if api_key:
        account = api_key_dec(api_key)
        if not account:
            raise ErrorResponse(Response(
                "API-KEY无效",
                status=403,
            ))
        user=await core.student.TABLE.get_user_info(account)
        if not user.name and not user.mail:
            raise ErrorResponse(Response(
                "User not Found",
                status=403,
            ))
        g.current_account = account
        return account
    raise ErrorResponse(
        Response(
            "UNAUTHORIZED: please set the 'X-API-KEY'"
            " in headers, cookies or query parameters.",
            status=401,
        )
    )


_CHECK_API_KEY_RESPONSES = {
    401: {"description": "未授权，没有提供 API-KEY"},
    403: {"description": "API-KEY 无效，用户不存在"},
}


class LoginBody(BaseModel):
    sid: str = Field(..., description="账户（学号）")
    pwd: str = Field(..., description="密码")


@WSGI.post(
    "/login",
    tags=[_TAG_LOGIN],
    responses={
        200: {
            "description": "登录成功返回 API-KEY",
            "content": {"text/plain": {}},
        },
        401: {"description": "密码错误"},
        403: {"description": "学生记录未找到"},
    },
)
async def login(body: LoginBody) -> Response:
    """登录，返回 API-KEY"""
    from util import api_key_enc

    try:
        if not await core.student.TABLE.check_password(body.sid, body.pwd):
            raise ErrorResponse(Response("UNAUTHORIZED: wrong password", status=401))
    except core.student.StudentNotFoundError:
        raise ErrorResponse(Response("student not found", status=403))

    return api_key_enc(body.sid), 200


# ==================================================================================== #
_TAG_USER = Tag(name="user", description="用户设置")


@WSGI.get(
    "/user",
    tags=[_TAG_USER],
    responses={
        200: {
            "description": "成功，返回当前用户信息",
            "content": {
                "application/json": {
                    "schema": core.student.UserInfo.model_json_schema()
                }
            },
        },
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def user_info():
    """获取用户信息"""
    account =await check_api_key()
    user = await core.student.TABLE.get_user_info(account)
    return user.model_dump()


@WSGI.put(
    "/user",
    tags=[_TAG_USER],
    responses={
        200: {"description": "修改成功"},
        400: {"description": "修改内容不合法"},
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def user_update(body: core.student.UserInfo):
    """修改用户信息"""
    account = await check_api_key()
    try:
        await core.student.TABLE.set_user_info(account, body)
        return _OK
    except core.student.StudentNotFoundError as e:
        raise ErrorResponse(Response(str(e), status=403))


class UserResetPassword(BaseModel):
    old_pwd: str = Field(..., description="旧密码")
    new_pwd: str = Field(..., description="新密码")


@WSGI.patch(
    "/user",
    tags=[_TAG_USER],
    responses={
        200: {"description": "修改成功"},
        400: {"description": "旧密码错误"},
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def user_reset_password(body: UserResetPassword):
    # """重置密码"""
    # pass    #TODO
    account = await check_api_key()
    try:
        if not await core.student.TABLE.check_password(account, body.old_pwd):
            raise ErrorResponse(Response("旧密码错误", status=400))
        await core.student.TABLE.reset_password(account, body.new_pwd)
        return _OK
    except core.student.StudentNotFoundError as e:
        raise ErrorResponse(Response(str(e), status=403))




# ==================================================================================== #
_TAG_CODESPACE = Tag(name="codespace", description="代码空间")


@WSGI.get(
    "/codespace",
    tags=[_TAG_CODESPACE],
    responses={
        302: {"description": "容器正在运行，重定向到代码空间页面"},
        303: {"description": "容器不在运行，重定向到代码空间管理页面"},
        307: {"description": "容器正在运行，但代码空间未启动"},
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def codespace():
    """进入代码空间（重定向）"""
    # pass    #TODO
    account=await check_api_key()
    space_status=await core.student.CODESPACE.get_status(account)
    url=await core.student.CODESPACE.get_url(account)

    if space_status=="running" and url:
        return redirect(url,code=302)
    elif space_status=="running" and not url:
        return redirect("/",code=307)
    else:
        return redirect("/",code=303)



@WSGI.post(
    "/codespace",
    tags=[_TAG_CODESPACE],
    responses={
        200: {"description": "启动操作成功"},
        202: {"description": "容器正在或已经启动"},
        402: {"description": "代码空间配额已耗尽"},
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def codespace_start():
    """启动代码空间，立即返回，不会等待代码空间启动完成"""
    pass    #TODO



@WSGI.delete(
    "/codespace",
    tags=[_TAG_CODESPACE],
    responses={
        200: {"description": "停止操作成功"},
        202: {"description": "容器不在运行"},
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def codespace_stop():
    """停止代码空间，立即返回，不会等待代码空间停止完成"""
    pass  # TODO


class CodespaceInfo(BaseModel):
    access_url: str | bool = Field(
        ...,
        description="访问链接，true 表示正在启动，false 表示不在运行",
    )

    last_start: float = Field(..., description="上次启动时间，POSIX 时间戳")
    last_stop: float = Field(..., description="上次停止时间，POSIX 时间戳")

    time_quota: float = Field(..., description="时间配额，单位秒")
    time_used: float = Field(..., description="已用时间，单位秒")
    space_quota: int = Field(..., description="空间配额，单位字节")
    space_used: int = Field(..., description="已用空间，单位字节")


@WSGI.get(
    "/codespace/info",
    tags=[_TAG_CODESPACE],
    responses={
        200: {
            "description": "成功返回代码空间信息",
            "content": {
                "application/json": {"schema": CodespaceInfo.model_json_schema()}
            },
        },
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def codespace_info():
    """获取代码空间信息"""
    pass  # TODO


@WSGI.post(
    "/codespace/keepalive",
    tags=[_TAG_CODESPACE],
    responses={
        200: {"description": "成功"},
        202: {"description": "代码空间不在运行"},
        **_CHECK_API_KEY_RESPONSES,
    },
    security=_SECURITY,
)
async def codespace_keepalive():
    """保持代码空间活跃，防止超时"""
    pass  # TODO


# ==================================================================================== #


def wsgi():
    import base.logger as logger
    from core import ainit
    logger.setup_logger(
        log_dir=CONFIG.log_dir,
        index_name="svc_stu",
    )
    LOGGER.info("Initializing student service...")
    RUNNER.run(ainit(cluster_mock=ENVIRON.mock_cluster))
    return WSGI


if __name__ == "__main__":
    from argparse import ArgumentParser

    argp = ArgumentParser()
    argp.add_argument("--nodbg", action="store_true")
    argp.add_argument("--port", type=int, default=5002)

    args = argp.parse_args()
    ARG_NODBG: bool = args.nodbg
    ARG_PORT: int = args.port

    wsgi().run(debug=not ARG_NODBG, port=ARG_PORT)
