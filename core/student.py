import os
from datetime import datetime
from typing import AsyncIterator, cast

from pydantic import BaseModel, Field, RootModel
from werkzeug.security import check_password_hash, generate_password_hash

import cluster
from base.logger import logger

from . import Error

LOGGERR = logger(__spec__, __file__)


class UserInfo(BaseModel):
    name: str = Field("", max_length=32, description="姓名")
    mail: str = Field("", max_length=32, description="邮箱")


class CodespaceInfo(BaseModel):
    status: str = Field("stopped", description="代码空间状态")
    url: str = Field("", description="代码空间URL")

    time_quota: int = Field(0, description="代码空间时间配额（秒）")
    time_used: int = Field(0, description="代码空间已使用时间（秒）")

    last_start: float = Field(0, description="代码空间最后启动的 POSIX 时间戳")
    last_stop: float = Field(0, description="代码空间最后停止的 POSIX 时间戳")
    last_active: float = Field(0, description="代码空间最后活动的 POSIX 时间戳")
    last_watch: float = Field(0, description="代码空间最后检查的 POSIX 时间戳")


class Student(BaseModel):
    """学生信息模型"""

    sid: str = Field(..., max_length=32, description="学号")
    pwd_hash: str = Field("", description="密码哈希")

    user_info: UserInfo = Field(default_factory=UserInfo, description="用户信息")
    codespace: CodespaceInfo = Field(
        default_factory=CodespaceInfo, description="代码空间信息"
    )

    def reset_password(self, new_password: str) -> None:
        """重置密码"""
        self.pwd_hash = generate_password_hash(new_password)

    def check_password(self, password: str) -> bool:
        """检查密码"""
        return check_password_hash(self.pwd_hash, password)

    def get_codespace_password(self) -> str:
        """获取代码空间密码"""
        from util import api_key_enc

        return api_key_enc(self.sid)


# ==================================================================================== #


class StudentNotFoundError(Error):
    """学生记录未找到"""

    def __init__(self, sid: str, *args):
        self.sid = sid
        super().__init__(*args)

    def __str__(self):
        return f"Student {self.sid!r} not found: {super().__str__()}"


class StudentAlreadyExistsError(Error):
    """学生记录已存在"""

    def __init__(self, sid: str, *args):
        self.sid = sid
        super().__init__(*args)

    def __str__(self):
        return f"Student {self.sid!r} already exists: {super().__str__()}"


class StudentDirectoryError(Error):
    """学生目录错误"""

    def __init__(self, sid: str, message: str, *args):
        self.sid = sid
        super().__init__(message, *args)

    def __str__(self):
        return f"Student {self.sid!r} directory error: {super().__str__()}"


# ==================================================================================== #


class TABLE:

    @classmethod
    async def read(cls, sid: str) -> Student:
        """读取学生记录"""
        from core import DB_STU

        keys = [
            "pwd_hash",
            "user_info.name",
            "user_info.mail",
            "codespace.status",
            "codespace.url",
            "codespace.last_start",
            "codespace.last_stop",
            "codespace.last_active",
            "codespace.last_watch",
        ]

        data = await DB_STU.hmget(sid, *keys)
        vmap = dict(zip(keys, data))
        if vmap["pwd_hash"] is None:
            raise StudentNotFoundError(sid)

        return Student(
            sid=sid,
            pwd_hash=vmap["pwd_hash"],
            user_info=UserInfo(
                name=vmap["user_info.name"], mail=vmap["user_info.mail"]
            ),
            codespace=CodespaceInfo(
                status=vmap["codespace.status"],
                url=vmap["codespace.url"],
                last_start=float(vmap["codespace.last_start"] or 0),
                last_stop=float(vmap["codespace.last_stop"] or 0),
                last_active=float(vmap["codespace.last_active"] or 0),
                last_watch=float(vmap["codespace.last_watch"] or 0),
            ),
        )

    @classmethod
    async def write(cls, student: Student) -> None:
        """写入学生记录"""
        from core import DB_STU

        data = {
            "pwd_hash": student.pwd_hash,
            "user_info.name": student.user_info.name,
            "user_info.mail": student.user_info.mail,
            "codespace.time_quota": student.codespace.time_quota,
            "codespace.time_used": student.codespace.time_used,
            "codespace.status": student.codespace.status,
            "codespace.url": student.codespace.url,
            "codespace.last_start": str(student.codespace.last_start),
            "codespace.last_stop": str(student.codespace.last_stop),
            "codespace.last_active": str(student.codespace.last_active),
            "codespace.last_watch": str(student.codespace.last_watch),
        }

        await DB_STU.hmset(student.sid, data)

    @classmethod
    async def iter_all(cls) -> AsyncIterator[Student]:
        """迭代所有学生记录"""
        from core import DB_STU

        async for sid in DB_STU.scan_iter():
            try:
                yield await cls.read(cast(str, sid))
            except StudentNotFoundError:
                LOGGERR.warning(f"Student {sid!r} not found during iteration")

    @classmethod
    async def all_ids(cls) -> list[str]:
        """获取所有学生ID"""
        from core import DB_STU

        return await DB_STU.keys()

    @classmethod
    async def create(cls, stu: Student) -> bool:
        """在数据库创建新的学生记录，在集群中分配存储空间"""
        from core import DB_STU

        from config import CONFIG

        if await DB_STU.exists(stu.sid):
            raise StudentAlreadyExistsError(stu.sid)

        stu_path = CONFIG.CORE.students_dir + stu.sid + "/"
        if not os.path.exists(stu_path):
            try:
                os.makedirs(stu_path)
                os.makedirs(stu_path + "code/")
                os.makedirs(stu_path + "io/")
                os.makedirs(stu_path + "root/")
            except:
                LOGGERR.error(f"Failed to create student directory {stu_path}")
                raise StudentDirectoryError(
                    stu.sid,
                    f"Failed to create student directory {stu_path}",
                )
        else:
            LOGGERR.warning(
                f"Student directory {stu_path} already exists, skipping creation"
            )

        ts = datetime.now().timestamp()
        stu.codespace.last_start = ts
        stu.codespace.last_stop = ts
        stu.codespace.last_active = ts
        stu.codespace.last_watch = ts

        await cls.write(stu)

        return True

    @classmethod
    async def delete(cls, sid: str) -> bool:
        """删除学生记录，归档代码空间，在集群中释放存储空间"""
        from core import DB_STU
        from config import CONFIG

        try:
            student = await cls.read(sid)
        except StudentNotFoundError:
            LOGGERR.warning(f"Student {sid!r} not found for deletion")
            return False

        # 归档代码空间

        # 移动学生目录到归档目录
        stu_path = CONFIG.CORE.students_dir + sid + "/"
        if os.path.exists(stu_path):
            os.rename(
                stu_path,
                CONFIG.CORE.archive_students_dir
                + sid
                + "_archived_"
                + datetime.now().isoformat(),
            )

        # 删除学生记录
        await DB_STU.delete(sid)
        return True

    @classmethod
    async def reset_password(cls, sid: str, new_password: str) -> None:
        """重置学生密码"""
        try:
            student = await cls.read(sid)
            student.reset_password(new_password)
            await cls.write(student)
        except StudentNotFoundError:
            LOGGERR.warning(f"尝试重置不存在的学生 {sid!r} 的密码")
            raise

    @classmethod
    async def check_password(cls, sid: str, password: str) -> bool:
        """检查学生密码"""
        try:
            student = await cls.read(sid)
            return student.check_password(password)
        except StudentNotFoundError:
            LOGGERR.warning(f"尝试验证不存在的学生 {sid!r} 的密码")
            return False

    @classmethod
    async def get_user_info(cls, sid: str) -> UserInfo:
        """获取学生用户信息"""
        try:
            student = await cls.read(sid)
            return student.user_info
        except StudentNotFoundError:
            LOGGERR.warning(f"尝试获取不存在的学生 {sid!r} 的用户信息")
            return UserInfo(name="", mail="")

    @classmethod
    async def set_user_info(cls, sid: str, user_info: UserInfo) -> None:
        """设置学生用户信息"""
        try:
            student = await cls.read(sid)
            student.user_info = user_info
            await cls.write(student)
        except StudentNotFoundError:
            LOGGERR.warning(f"尝试更新不存在的学生 {sid!r} 的用户信息")
            raise


class CODESPACE:

    @classmethod
    async def start(cls, sid: str) -> None:
        """启动代码空间"""
        #TODO
        pass

    @classmethod
    async def stop(cls, sid: str) -> None:
        """停止代码空间"""
        #TODO
        pass

    @classmethod
    async def get_status(cls, sid: str) -> str:
        """获取代码空间状态"""
        #TODO
        return "stopped"

    @classmethod
    async def get_url(cls, sid: str) -> str | bool:
        """获取代码空间URL"""
        #TODO
        return "http://example.com/codespace"

    @classmethod
    async def watch(cls, sid: str) -> None:
        """监控代码空间活动状态，更新最后活动时间，停止空闲作业"""
        #TODO
        pass

    @classmethod
    async def keep_alive(cls, sid: str) -> None:
        """保持代码空间活跃，更新最后活动时间"""
        #TODO
        pass
