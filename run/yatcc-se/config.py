"""YatCC-SE 生产基准配置"""

import os
from base import Configuration


class Environ(Configuration):
    is_k8s = "KUBERNETES_SERVICE_HOST" in os.environ
    mock_cluster = not is_k8s


ENVIRON = Environ()


class Config(Configuration):
    app_dir = "/app/"
    io_dir = "/io/"
    log_dir = "/io/log/"
    run_dir = "/run/yatcc-se/"
    log_level = 1

    api_key_secret = (
        b"\xd2\xb6J!\xaf\xa5\xd9\x94'\xb3S4=\x12\xa2\x1c|"
        b"g\xf4\xbf\x82*R\xecT\x85W\x96\xee\x04\\\x8d"
    )

    CORE: type["Core"]
    SVC_STU: type["SvcStu"]
    SVC_ADM: type["SvcAdm"]
    ENTRY: type["Entry"]


CONFIG = Config()


class Core(Configuration):
    redis_init: dict = {
        "unix_socket_path": Config.io_dir + "run/redis.sock",
        "decode_responses": False,
    }

    students_dir = Config.io_dir + "students/"
    archive_students_dir = Config.io_dir + "archive-students/"

    default_admin_api_key = "SE!@2025"


CONFIG.CORE = Core


class SvcStu(Configuration):

    static_dir = "/app/stu-site/dist"


CONFIG.SVC_STU = SvcStu


class SvcAdm(Configuration):

    static_dir = "/app/adm-site/dist"


CONFIG.SVC_ADM = SvcAdm


class Entry(Configuration):

    redis_executable = "/usr/bin/redis-server"
    sshd_executable = "" if ENVIRON.is_k8s else "/usr/sbin/sshd"

    health_check_interval = 60
    startup_integrity_check: bool | None = None

    svc_adm_workers = 2
    svc_stu_workers = 4

    default_watching_students_interval = 60 * 15

CONFIG.ENTRY = Entry

class ClusterConfig(Configuration):
    """集群配置"""

    DEFAULT_TYPE = "mock"

    class Kubernetes(Configuration):
        NAMESPACE = "default"
        KUBECONFIG_PATH = None
        TIMEOUT = 30

    class Codespace(Configuration):
        """codespace 配置"""

        IMAGE = "nickchencoffee/codespace:aarch64"
        DEFAULT_PASSWORD = "student123"
        DEFAULT_CPU_LIMIT = "1000m"
        DEFAULT_MEMORY_LIMIT = "2Gi"
        DEFAULT_STORAGE_SIZE = "5Gi"
        PORT = [
            {
                "port": 443,
                "targetPort": 443,
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
