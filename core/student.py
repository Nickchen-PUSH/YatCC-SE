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


class CodespaceQuotaExceededError(Error):
    """代码空间配额已用尽错误"""
    
    def __init__(self, sid: str, *args):
        self.sid = sid
        super().__init__(*args)
    
    def __str__(self) -> str:
        return f"Codespace quota exceeded: {self.sid}"


class CodespaceStartError(Error):
    """代码空间启动错误"""
    
    def __init__(self, sid: str, reason: str, *args):
        self.sid = sid
        self.reason = reason
        super().__init__(*args)
    
    def __str__(self) -> str:
        return f"Failed to start codespace: {self.sid}, reason: {self.reason}"


class CodespaceStopError(Error):
    """代码空间停止错误"""
    
    def __init__(self, sid: str, reason: str, *args):
        self.sid = sid
        self.reason = reason
        super().__init__(*args)
    
    def __str__(self) -> str:
        return f"Failed to stop codespace: {self.sid}, reason: {self.reason}"

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
            "codespace.time_quota",
            "codespace.time_used",
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
                time_quota=int(vmap["codespace.time_quota"] or 0),
                time_used=int(vmap["codespace.time_used"] or 0),
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
        from core import CLUSTER
        
        try:
            # 获取学生信息
            student = await TABLE.read(sid)
            
            # 如果代码空间已在运行，则无需再次启动
            if student.codespace.status == "running":
                LOGGERR.info(f"代码空间已经在运行中: {sid}")
                return
                
            # 检查时间配额
            if student.codespace.time_quota > 0 and student.codespace.time_used >= student.codespace.time_quota:
                LOGGERR.warning(f"学生代码空间时间配额已用尽: {sid}")
                raise CodespaceQuotaExceededError(sid)
                
            # 准备作业参数
            job_params = cluster.JobParams(
                name=f"codespace-{sid}",
                image="codespace-base:latest",  # 使用默认的代码空间镜像
                ports=[8080, 22],  # 默认映射Web端口和SSH端口
                env={
                    "STUDENT_ID": sid,
                    "USER_NAME": student.user_info.name,
                    "PASSWORD": student.get_codespace_password()
                },
                user_id=sid  # 添加必需的user_id字段
            )
            
            # 提交作业到集群
            LOGGERR.info(f"正在启动学生代码空间: {sid}")
            job_info = await CLUSTER.submit_job(job_params)
            
            # 更新代码空间信息
            now = datetime.now().timestamp()
            student.codespace.status = "running"
            student.codespace.url = f"http://localhost:{job_info.ports[0]}"  # 使用第一个端口作为Web访问URL
            student.codespace.last_start = now
            student.codespace.last_active = now
            
            # 将作业ID存储在Redis中，用于后续操作
            from core import DB_STU
            await DB_STU.set(f"{sid}:job_id", job_info.id)
            
            # 保存更新后的学生信息
            await TABLE.write(student)
            LOGGERR.info(f"学生代码空间启动成功: {sid}, job_id: {job_info.id}")
            
        except StudentNotFoundError:
            LOGGERR.error(f"找不到学生: {sid}")
            raise
        except CodespaceQuotaExceededError:
            LOGGERR.error(f"学生代码空间配额已用尽: {sid}")
            raise
        except Exception as e:
            LOGGERR.error(f"启动学生代码空间失败: {sid}, 错误: {e}")
            # 确保发生错误时代码空间状态被设置为stopped
            try:
                student = await TABLE.read(sid)
                student.codespace.status = "stopped"
                await TABLE.write(student)
            except:
                pass
            raise CodespaceStartError(sid, str(e))

    @classmethod
    async def stop(cls, sid: str) -> None:
        """停止代码空间"""
        from core import CLUSTER, DB_STU
        
        try:
            # 获取学生信息
            student = await TABLE.read(sid)
            
            # 如果代码空间已经停止，则无需操作
            if student.codespace.status == "stopped":
                LOGGERR.info(f"代码空间已经停止: {sid}")
                return
            
            # 获取作业ID
            job_id = await DB_STU.get(f"{sid}:job_id")
            if not job_id:
                LOGGERR.warning(f"找不到学生代码空间的作业ID: {sid}")
                # 即使找不到作业ID，也更新状态为stopped
                student.codespace.status = "stopped"
                await TABLE.write(student)
                return
            
            # 调用集群接口停止作业
            LOGGERR.info(f"正在停止学生代码空间: {sid}, job_id: {job_id}")
            await CLUSTER.delete_job(job_id)
            
            # 更新代码空间信息
            now = datetime.now().timestamp()
            student.codespace.status = "stopped"
            student.codespace.url = ""
            student.codespace.last_stop = now
            
            # 计算本次使用的时间并更新总使用时间
            if student.codespace.last_start > 0:
                used_time = now - student.codespace.last_start
                student.codespace.time_used += int(used_time)
                LOGGERR.info(f"代码空间使用时间更新: {sid}, +{int(used_time)}秒, 总计{student.codespace.time_used}秒")
            
            # 删除Redis中存储的作业ID
            await DB_STU.delete(f"{sid}:job_id")
            
            # 保存更新后的学生信息
            await TABLE.write(student)
            LOGGERR.info(f"学生代码空间停止成功: {sid}")
            
        except StudentNotFoundError:
            LOGGERR.error(f"找不到学生: {sid}")
            raise
        except Exception as e:
            LOGGERR.error(f"停止学生代码空间失败: {sid}, 错误: {e}")
            try:
                # 尝试更新状态为stopped，确保一致性
                student = await TABLE.read(sid)
                student.codespace.status = "stopped"
                await TABLE.write(student)
            except:
                pass
            raise CodespaceStopError(sid, str(e))

    @classmethod
    async def get_status(cls, sid: str) -> str:
        """获取代码空间状态"""
        from core import CLUSTER, DB_STU
        
        try:
            # 获取学生信息
            student = await TABLE.read(sid)
            
            # 如果数据库中记录的状态是stopped，直接返回
            if student.codespace.status == "stopped":
                return "stopped"
            
            # 如果状态是running，检查作业实际状态
            # 获取作业ID
            job_id = await DB_STU.get(f"{sid}:job_id")
            if not job_id:
                # 没有作业ID但状态是running，说明数据不一致
                LOGGERR.warning(f"代码空间状态不一致: {sid}, 状态为running但找不到作业ID")
                # 更新状态为stopped
                student.codespace.status = "stopped"
                await TABLE.write(student)
                return "stopped"
            
            try:
                # 从集群获取作业状态
                job_status = await CLUSTER.get_job_status(job_id)
                
                # 映射集群作业状态到代码空间状态
                if job_status == cluster.JobInfo.Status.RUNNING:
                    return "running"
                elif job_status == cluster.JobInfo.Status.PENDING:
                    return "starting"
                else:
                    # 作业已结束或失败，更新状态为stopped
                    LOGGERR.info(f"代码空间作业已结束: {sid}, job_id: {job_id}, status: {job_status}")
                    student.codespace.status = "stopped"
                    await TABLE.write(student)
                    return "stopped"
                    
            except Exception as e:
                # 获取作业状态失败，假设作业不存在或已停止
                LOGGERR.warning(f"获取代码空间作业状态失败: {sid}, job_id: {job_id}, 错误: {e}")
                student.codespace.status = "stopped"
                await TABLE.write(student)
                return "stopped"
            
            # 返回数据库中记录的状态作为默认值
            return student.codespace.status
            
        except StudentNotFoundError:
            LOGGERR.error(f"找不到学生: {sid}")
            raise
        except Exception as e:
            LOGGERR.error(f"获取代码空间状态失败: {sid}, 错误: {e}")
            return "error"

    @classmethod
    async def get_url(cls, sid: str) -> str | bool:
        """获取代码空间URL
        
        返回值:
            str: 代码空间正在运行时的访问URL
            True: 代码空间正在启动中
            False: 代码空间已停止或不可用
        """
        from core import DB_STU
        
        try:
            # 获取学生信息
            student = await TABLE.read(sid)
            
            # 获取当前代码空间状态
            status = await cls.get_status(sid)
            
            if status == "stopped":
                # 代码空间已停止，返回False
                return False
            elif status == "starting":
                # 代码空间正在启动，返回True
                return True
            elif status == "running":
                # 代码空间正在运行，返回URL
                
                # 检查是否有存储的URL
                if student.codespace.url and student.codespace.url.strip():
                    return student.codespace.url
                
                # 尝试从作业ID构建URL
                job_id = await DB_STU.get(f"{sid}:job_id")
                if not job_id:
                    LOGGERR.warning(f"代码空间状态不一致: {sid}, 状态为running但找不到作业ID")
                    return False
                
                # 如果没有URL但有作业ID，使用存储的URL或构建一个默认URL
                if not student.codespace.url or not student.codespace.url.strip():
                    # 构造一个默认的URL，实际应用中应根据实际环境配置
                    from config import CONFIG
                    base_url = getattr(CONFIG.CORE, 'codespace_base_url', 'http://localhost')
                    port = 8080  # 默认端口
                    student.codespace.url = f"{base_url}:{port}/codespace/{sid}"
                    await TABLE.write(student)
                    LOGGERR.info(f"为学生代码空间创建默认URL: {sid}, URL: {student.codespace.url}")
                    
                return student.codespace.url
                
            else:
                # 未知状态，返回False
                LOGGERR.warning(f"未知的代码空间状态: {sid}, status: {status}")
                return False
                
        except StudentNotFoundError:
            LOGGERR.error(f"找不到学生: {sid}")
            raise
        except Exception as e:
            LOGGERR.error(f"获取代码空间URL失败: {sid}, 错误: {e}")
            return False
            
        # 默认情况返回False
        return False

# 下面的先不实现
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
