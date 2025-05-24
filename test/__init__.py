import os
from pathlib import Path

from base import PROJECT_DIR, RUNNER, guard_once
from config import ENVIRON

TESTING_DIR = PROJECT_DIR / "testing"
TESTING_ROOT = True
os.environ["YatCC_OL_TESTING"] = str(TESTING_DIR)


# ==================================================================================== #
# 异步测试支持
# ==================================================================================== #
import asyncio as aio
import inspect
import unittest


class AsyncTestCase(unittest.TestCase):

    def _callTestMethod(self, method):
        global RUNNER

        if inspect.iscoroutinefunction(method):
            RUNNER.run(method())
        else:
            method()


# ==================================================================================== #
# 模块初始化助手
# ==================================================================================== #
import cluster

CLUSTER: cluster.ClusterABC

REDIS_SOCK = str(TESTING_DIR / "redis.sock")
REDIS_INIT = {"unix_socket_path": REDIS_SOCK}

@guard_once
def setup_test(test_name: str):
    """设置测试环境"""

    from shutil import rmtree

    from base.logger import setup_logger

    if TESTING_ROOT:
        rmtree(TESTING_DIR, ignore_errors=True)
        TESTING_DIR.mkdir(exist_ok=True)
    setup_logger(TESTING_DIR / "log", test_name, level=1)

@guard_once
async def ainit_redis_server():
    """启动测试用 redis-server"""

    pid_file = str(TESTING_DIR / "redis.pid")
    assert not os.path.exists(pid_file), "测试用 redis-server 已经启动"

    conf = f"""
bind 127.0.0.1 -::1
port 0
unixsocket {REDIS_SOCK}
unixsocketperm 777
timeout 0
daemonize no
pidfile {pid_file}
loglevel debug
logfile ""
databases 16
save ""
appendonly no
"""
    with open(TESTING_DIR / "redis.conf", "w") as f:
        f.write(conf)
    stdout = open(TESTING_DIR / "redis.stdout", "wb")
    stderr = open(TESTING_DIR / "redis.stderr", "wb")
    with stdout, stderr:
        ps = await aio.subprocess.create_subprocess_exec(
            ENVIRON.EXECUTABLE.redis_server,
            TESTING_DIR / "redis.conf",
            stdout=stdout,
            stderr=stderr,
        )

    from atexit import register

    def atexit():
        nonlocal ps
        from signal import SIGTERM

        ps.send_signal(SIGTERM)
        assert RUNNER.run(ps.wait()) == 0

    register(atexit)

    import redis.asyncio

    db = redis.asyncio.Redis(**REDIS_INIT)
    for _ in range(50):
        await aio.sleep(0.1)
        try:
            await db.ping()
            break
        except redis.exceptions.ConnectionError:
            pass
    else:
        assert False, "启动测试用 redis-server 超时"

@guard_once
async def ainit_cluster() -> cluster.ClusterABC:
    global CLUSTER
    from cluster import create

    CLUSTER = create(
        mock=ENVIRON.mock_cluster,
    )

    return CLUSTER


@guard_once
async def ainit_core() -> None:
    """初始化系统核心模块"""

    from core import ainit, ready

    from .. import ENVIRON

    await ainit_redis_server()
    await ainit(cluster_mock=not ENVIRON.test_external)
    for _ in range(50):
        await aio.sleep(0.1)
        if await ready():
            break
    else:
        assert False, "系统核心模块初始化超时"