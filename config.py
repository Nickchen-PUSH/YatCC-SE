import os
import platform
from pathlib import Path
from types import ModuleType

from base import PROJECT_DIR, Configuration, timetag

REDIS_SVC_LINUX = "/usr/bin/redis-server"
REDIS_SVC_MAC = "/opt/homebrew/bin/redis-server"
# ==================================================================================== #

class Environ(Configuration):
    mock_cluster = True

    EXECUTABLE: type["Executable"]
    """外部可执行程序"""

ENVIRON = Environ

class Executable(Configuration):
    # 根据不同的平台设置不同的可执行文件
    system = platform.system().lower()
    if system == "linux":
        redis_server = REDIS_SVC_LINUX
    elif system == "darwin":
        redis_server = REDIS_SVC_MAC
    else:
        redis_server = REDIS_SVC_MAC

ENVIRON.EXECUTABLE = Executable

# ==================================================================================== #


class Config(Configuration):
    app_dir = str(PROJECT_DIR) + "/"
    """应用程序目录，必须以 / 结尾"""
    io_dir = str((PROJECT_DIR / "running") / "io") + "/"
    """输入输出目录，必须以 / 结尾"""
    log_dir = io_dir + "log/"
    """日志目录，必须以 / 结尾"""
    log_level = 1
    """日志级别"""
    api_key_secret = b"\x00" * 32
    """用于加密 API-KEY 的密钥，必须是 32 字节"""
    
    CORE: type["Core"]
    """核心模块配置"""


CONFIG = Config

class Core(Configuration):
    redis_init: dict = (
        {
            "host": "localhost",
            "port": 6379,
            "decode_responses": False,
        }
    )
    """Redis 初始化参数"""

    students_dir = Config.io_dir + "students/"
    """学生数据的存储目录，必须以 / 结尾"""
    archive_students_dir = Config.io_dir + "archive-students/"
    """学生数据的归档目录，必须以 / 结尾"""

CONFIG.CORE = Core