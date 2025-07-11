"""CODESPACE 配置基准，同时支持开发环境、测试环境和生产环境。

注意：为了能将系统运行所需要的一切配置都写在这里，这个文件不能导入
系统的任何功能模块，只能导入第三方库、自定义的配置文件等。
"""

import os
from pathlib import Path
from types import ModuleType

from base import PROJECT_DIR, Configuration, timetag

try:
    from config import ENVIRON
except ImportError:
    ENVIRON = None


TESTING: ModuleType | None = None
TESTING_DIR: Path | None = None
if v := os.getenv("YatCC_CS_TESTING"):
    TESTING_DIR = Path(v)
    try:
        import test

        TESTING = test
    except ImportError:
        pass


# ==================================================================================== #


class Config(Configuration):
    # app_dir = str(PROJECT_DIR) + "/"
    app_dir = "/app/"
    """应用程序目录，必须以 / 结尾"""
    # io_dir = str((TESTING_DIR or PROJECT_DIR / "tmp") / "io") + "/"
    io_dir = "/io/"
    """输入输出目录，必须以 / 结尾"""
    log_dir = io_dir + "log/"
    """日志目录，必须以 / 结尾"""
    log_level = 1
    """日志级别"""

    ENTRY: type["Entry"]
    """入口程序配置"""


CONFIG = Config


class Entry(Configuration):
    sshd_executable: str | None = (
        ENVIRON.EXECUTABLE.sshd if ENVIRON else "/usr/sbin/sshd"
    )
    """SSH 服务可执行程序"""


CONFIG.ENTRY = Entry


# ==================================================================================== #

try:
    from .config import CONFIG as APP_CONFIG

    CONFIG.overlay(APP_CONFIG)
except ImportError:
    pass
try:
    from .config import IO_CONFIG

    CONFIG.overlay(IO_CONFIG)
except ImportError:
    pass

if v := os.getenv("CS_LOG_DIR"):
    CONFIG.log_dir = v
else:
    CONFIG.log_dir += timetag(us=True) + "/"
    os.environ["CS_LOG_DIR"] = CONFIG.log_dir
