"""YatCC-SE 生产基准配置"""

from base import Configuration


class Config(Configuration):
    app_dir = "/app/"
    io_dir = "/io/"
    log_dir = "/io/log/"
    log_level = 1

    api_key_secret = (
        b"\xd2\xb6J!\xaf\xa5\xd9\x94'\xb3S4=\x12\xa2\x1c|"
        b"g\xf4\xbf\x82*R\xecT\x85W\x96\xee\x04\\\x8d"
    )

    CORE: type["Core"]
    SVC_STU: type["SvcStu"]
    SVC_ADM: type["SvcAdm"]
    ENTRY: type["Entry"]


CONFIG = Config


class Core(Configuration):

    students_dir = Config.io_dir + "students/"
    archive_students_dir = Config.io_dir + "archive-students/"

    default_admin_api_key = "SE!@2025"


CONFIG.CORE = Core


class SvcStu(Configuration):

    static_dir = "/app/stu-site"


CONFIG.SVC_STU = SvcStu


class SvcAdm(Configuration):

    static_dir = "/app/adm-site"


CONFIG.SVC_ADM = SvcAdm


class Entry(Configuration):

    redis_executable = "/usr/bin/redis-server"
    sshd_executable = "/usr/sbin/sshd"


CONFIG.ENTRY = Entry


# ==================================================================================== #
import sys

# 尝试加载外部配置
try:
    import importlib.util

    spec = importlib.util.spec_from_file_location("io_config", "/io/config.py")
    assert spec, "io_config not found"

    io_config = importlib.util.module_from_spec(spec)
    sys.modules["io_config"] = io_config

    assert spec.loader, "io_config loader not found"
    spec.loader.exec_module(io_config)

    IO_CONFIG: Configuration = io_config.CONFIG
except Exception:
    pass
