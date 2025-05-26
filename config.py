import os
from pathlib import Path
from types import ModuleType

from base import PROJECT_DIR, Configuration, timetag

# ==================================================================================== #

class Environ(Configuration):
    mock_cluster = True

    EXECUTABLE: type["Executable"]
    """外部可执行程序"""

ENVIRON = Environ

class Executable(Configuration):
    redis_server = "/opt/homebrew/bin/redis-server"


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

# ==================================================================================== #
import asyncio as aio

RUNNER = aio.Runner()
"""系统全局的异步运行器

绝大多数情况下，这个运行器都不必直接使用：在异步函数里可以使用 aio.get_event_loop()
来获取当前事件循环；初始化函数可以定义为异步的从而将异步执行器的选择推迟给调用者。

只有在必须从同步代码中调用异步函数时，才需要直接使用它 —— 也必须使用它，而不能是
aio.run 等其他运行器，因为系统初始化后创建的全局变量很多都会与运行器绑定。
"""
