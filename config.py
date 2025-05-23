import os
from pathlib import Path
from types import ModuleType

from base import PROJECT_DIR, Configuration, timetag

# ==================================================================================== #


class Config(Configuration):
    app_dir = str(PROJECT_DIR) + "/"
    """应用程序目录，必须以 / 结尾"""
    io_dir = str((PROJECT_DIR / "running/YatCC-OL") / "io") + "/"
    """输入输出目录，必须以 / 结尾"""
    log_dir = io_dir + "log/"
    """日志目录，必须以 / 结尾"""
    log_level = 1
    """日志级别"""

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