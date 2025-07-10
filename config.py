import os
from pathlib import Path
from types import ModuleType

from base import PROJECT_DIR, Configuration, timetag

# ==================================================================================== #


class Environ(Configuration):
    mock_cluster = False

    EXECUTABLE: type["Executable"]
    """外部可执行程序"""


ENVIRON = Environ


class Executable(Configuration):
    rm = "/bin/rm"
    cp = "/bin/cp"
    tar = "/usr/bin/tar"
    npm = "/opt/homebrew/bin/npm"
    wget = "/opt/homebrew/bin/wget"
    docker = "/usr/local/bin/docker"
    redis_server = "/opt/homebrew/bin/redis-server"
    sshd = ""


ENVIRON.EXECUTABLE = Executable


# ==================================================================================== #


class Config(Configuration):
    app_dir = str(PROJECT_DIR) + "/"
    """应用程序目录，必须以 / 结尾"""
    io_dir = str((PROJECT_DIR / "running") / "io") + "/"
    """输入输出目录，必须以 / 结尾"""
    log_dir = io_dir + "log/"
    """日志目录，必须以 / 结尾"""
    run_dir = io_dir + "run/"
    """运行时目录，必须以 / 结尾"""
    log_level = 1
    """日志级别"""
    api_key_secret = b"\x00" * 32
    """用于加密 API-KEY 的密钥，必须是 32 字节"""

    CORE: type["Core"]
    """核心模块配置"""

    CLUSTER: type["ClusterConfig"]
    """集群配置"""

    ENTRY: type["Entry"]
    """入口程序配置"""

    SVC_STU: type["SvcStu"]
    """学生服务配置"""

    SVC_ADM: type["SvcAdm"]
    """管理员服务配置"""


CONFIG = Config


class Core(Configuration):
    redis_init: dict = {
        "unix_socket_path": Config.io_dir + "run/redis.sock",
        "decode_responses": False,
    }
    """Redis 初始化参数"""

    students_dir = Config.io_dir + "students/"
    """学生数据的存储目录，必须以 / 结尾"""
    archive_students_dir = Config.io_dir + "archive-students/"
    """学生数据的归档目录，必须以 / 结尾"""


CONFIG.CORE = Core

# ==================================================================================== #


class SvcStu(Configuration):
    static_dir = str(PROJECT_DIR / "stu-site/dist")
    """前端静态站点目录路径"""


CONFIG.SVC_STU = SvcStu


class SvcAdm(Configuration):
    static_dir = str(PROJECT_DIR / "adm-site/dist")
    """前端静态站点目录路径"""


CONFIG.SVC_ADM = SvcAdm


# ==================================================================================== #


class Entry(Configuration):
    redis_executable: str = ENVIRON.EXECUTABLE.redis_server if ENVIRON else ""
    """Redis 服务可执行程序"""
    sshd_executable: str | None = ENVIRON.EXECUTABLE.sshd if ENVIRON else None
    """SSH 服务可执行程序"""

    health_check_interval = 60
    """系统健康检查间隔（秒）"""
    startup_integrity_check: bool | None = None
    """启动时完整性检查：True 启用，False 禁用，None 由系统自行决定"""

    svc_adm_workers = 2
    """管理员服务的工作进程数"""
    svc_stu_workers = 4
    """学生服务的工作进程数"""

    default_watching_students_interval = 60 * 15
    """默认的学生监控间隔（秒）"""


CONFIG.ENTRY = Entry

# ==================================================================================== #


class ClusterConfig(Configuration):
    """集群配置"""

    DEFAULT_TYPE = "mock"

    class Kubernetes(Configuration):
        NAMESPACE = "default"
        KUBECONFIG_PATH = None
        TIMEOUT = 30

    class Codespace(Configuration):
        """codespace 配置"""

        IMAGE = "codercom/code-server:latest"
        DEFAULT_PASSWORD = "student123"
        DEFAULT_CPU_LIMIT = "1000m"
        DEFAULT_MEMORY_LIMIT = "2Gi"
        DEFAULT_STORAGE_SIZE = "5Gi"
        PORT = [
            {
                "port": 8080,
                "targetPort": 8080,
                "name": "http",
            },
            {
                "port": 5900,
                "targetPort": 5900,
                "name": "vnc",
            },
            {
                "port": 22,
                "targetPort": 22,
                "name": "ssh",
            },
        ]


CONFIG.CLUSTER = ClusterConfig
