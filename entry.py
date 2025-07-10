import asyncio as aio
import os
import sys

import core
from base import entry
from base.logger import logger
from base.progress import PROGRESS

from config import CONFIG, ENVIRON

LOGGER = logger(__spec__, __file__)

SSH_SERVER: aio.subprocess.Process | None
REDIS_SERVER: aio.subprocess.Process
SVC_ADM: aio.subprocess.Process
SVC_STU: aio.subprocess.Process


async def start() -> None:
    assert CONFIG.log_dir.endswith("/")

    ######
    os.makedirs(CONFIG.log_dir, exist_ok=True)
    CONFIG.markdown(CONFIG.log_dir + "config.md")

    ######
    global SSH_SERVER
    if not CONFIG.ENTRY.sshd_executable:
        SSH_SERVER = None
        PROGRESS("SSH 服务已禁用", logger=LOGGER)
    else:
        with PROGRESS["启动 SSH 服务", LOGGER]:
            os.makedirs("/run/sshd", exist_ok=True)
            # sshd 需要 /run/sshd 目录来权限分离

            ssh_log = CONFIG.log_dir + "sshd.log"
            os.mknod(rmfile(ssh_log), 0o644)
            # 允许其它用户读取日志，sshd 创建的默认是 600 权限

            SSH_SERVER = await entry.start_subp(
                LOGGER,
                CONFIG.ENTRY.sshd_executable,
                "-D",
                *["-E", ssh_log],
                *["-f", mk_sshd_config()],
                cwd=CONFIG.io_dir,
                stdout=CONFIG.log_dir + "sshd.out.start",
                stderr=CONFIG.log_dir + "sshd.err.start",
            )
            PROGRESS(f"PID: {SSH_SERVER.pid}")

    ######
    global REDIS_SERVER
    with PROGRESS["启动 Redis 服务", LOGGER]:
        REDIS_SERVER = await entry.start_subp(
            LOGGER,
            CONFIG.ENTRY.redis_executable,
            mk_redis_config(),
            cwd=CONFIG.io_dir,
            stdout=CONFIG.log_dir + "redis.out.start",
            stderr=CONFIG.log_dir + "redis.err.start",
        )
        PROGRESS(f"PID: {REDIS_SERVER.pid}")

        with PROGRESS["等待服务就绪", LOGGER]:
            await core.ainit(cluster_mock=ENVIRON.mock_cluster)
            for i in PROGRESS @ range(30):
                await aio.sleep(0.1)
                if await core.ready():
                    break
                PROGRESS(f"等待 Redis 服务 {i}", logger=LOGGER)
            else:
                raise TimeoutError(PROGRESS("Redis 服务启动超时", logger=LOGGER))
            PROGRESS("Redis 服务已就绪", logger=LOGGER)

    # integrity_check = False
    # if CONFIG.ENTRY.startup_integrity_check is None:
    #     if not await core.INTEGRITY.get():
    #         PROGRESS("Redis 数据库可能不完整，启动检查")
    #         integrity_check = True
    # elif CONFIG.ENTRY.startup_integrity_check:
    #     integrity_check = True
    # if integrity_check:
    #     with PROGRESS["检查 Redis 数据库完整性", LOGGER]:
    #         if await core.integritize():
    #             PROGRESS("成功")
    #         else:
    #             PROGRESS("失败", logger=LOGGER)
    #             raise RuntimeError("Redis 数据库完整性检查失败")

    ######
    global SVC_ADM, SVC_STU
    with PROGRESS["启动管理员和学生的 Web 服务", LOGGER]:
        rmfile("/run/svc_adm.pid")
        rmfile("/run/svc_stu.pid")
        # 删除可能残留的 PID 文件，这会导致 Gunicorn 启动失败

        SVC_ADM, SVC_STU = await aio.gather(
            entry.start_subp(
                LOGGER,
                sys.executable,
                *["-m", "gunicorn"],
                *["-b", "0.0.0.0:5001"],
                # TODO HTTPS 测试未通过，暂时使用 HTTP
                *["-w", str(CONFIG.ENTRY.svc_adm_workers)],
                *["-p", "/run/svc_adm.pid"],
                *["--access-logfile", CONFIG.log_dir + "svc_adm.access.log"],
                *["--error-logfile", CONFIG.log_dir + "svc_adm.error.log"],
                "svc_adm:wsgi()",
                cwd=CONFIG.app_dir,
                stdout=CONFIG.log_dir + "svc_adm.out.start",
                stderr=CONFIG.log_dir + "svc_adm.err.start",
            ),
            entry.start_subp(
                LOGGER,
                sys.executable,
                *["-m", "gunicorn"],
                *["-b", "0.0.0.0:5002"],
                *["-w", str(CONFIG.ENTRY.svc_stu_workers)],
                *["-p", "/run/svc_stu.pid"],
                *["--access-logfile", CONFIG.log_dir + "svc_stu.access.log"],
                *["--error-logfile", CONFIG.log_dir + "svc_stu.error.log"],
                "svc_stu:wsgi()",
                cwd=CONFIG.app_dir,
                stdout=CONFIG.log_dir + "svc_stu.out.start",
                stderr=CONFIG.log_dir + "svc_stu.err.start",
            ),
        )
        PROGRESS(f"PID: {SVC_ADM.pid}, {SVC_STU.pid}")

    ######
    aio.create_task(run(), name="run")


async def stop():
    """停止系统时执行（优雅退出）"""

    ######
    global SVC_ADM, SVC_STU
    with PROGRESS["停止管理员和学生的 Web 服务", LOGGER]:
        (adm_ok, adm_res), (stu_ok, stu_res) = await aio.gather(
            entry.stop_subp(SVC_ADM, timeout=1),
            entry.stop_subp(SVC_STU, timeout=1),
        )
        if not adm_ok or adm_res != 0:
            PROGRESS(f"管理员 Web 服务异常退出，退出码 {adm_res}", logger=LOGGER)
        if not stu_ok or stu_res != 0:
            PROGRESS(f"学生 Web 服务异常退出，退出码 {stu_res}", logger=LOGGER)

    ######
    global REDIS_SERVER
    from . import core

    with PROGRESS["停止 Redis 服务", LOGGER]:
        redis_ok, redis_res = await entry.stop_subp(REDIS_SERVER, timeout=3)
        if not redis_ok or redis_res != 0:
            PROGRESS(f"Redis 服务异常退出，退出码 {redis_res}", logger=LOGGER)

    ######
    global SSH_SERVER
    if SSH_SERVER is not None:
        with PROGRESS["停止 SSH 服务", LOGGER]:
            sshd_ok, sshd_res = await entry.stop_subp(SSH_SERVER, timeout=1)
            if not sshd_ok or sshd_res != 0:
                PROGRESS(f"SSH 服务异常退出，退出码 {sshd_res}", logger=LOGGER)


async def run():
    """在系统运行期间执行"""

    from .core import student

    await aio.sleep(3)  # 等待服务就绪

    while True:
        try:
            await student.CODESPACE.watch_all()
        except Exception as e:
            LOGGER.error(f"监控学生代码空间时发生错误: {e}")
        await aio.sleep(60)  # 每60秒检查一次


# ==================================================================================== #
from textwrap import dedent


def rmfile(path: str) -> str:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    return path


def mk_redis_config() -> str:
    path = CONFIG.log_dir + "redis.conf"
    try:
        f = open(path, "x")
    except FileExistsError:
        return path
    with f:
        f.write(
            dedent(
                f"""
                bind 127.0.0.1 -::1
                port 6379
                tcp-backlog 511
                timeout 0
                tcp-keepalive 300
                daemonize no
                pidfile /run/redis.pid
                loglevel notice
                logfile "{CONFIG.log_dir + "redis.log"}"
                """
                """
                databases 4
                """  # 数据库数量，这个值很重要，需要与核心模块对应
                """
                always-show-logo no
                save 3600 1 300 100 60 10000
                stop-writes-on-bgsave-error yes
                rdbcompression yes
                rdbchecksum yes
                """
                """
                dbfilename state.rdb
                """  # 持久化的数据库文件名
                f"""
                dir "{CONFIG.io_dir}"
                """  # 工作目录，结合 dbfilename 可以确定 RDB 文件的位置
                """
                appendonly no
                """  # 关闭 AOF 持久化
            )
        )
    return path


def mk_sshd_config() -> str:
    path = CONFIG.log_dir + "sshd_config"
    try:
        f = open(path, "x")
    except FileExistsError:
        return path
    with f:
        f.write(
            dedent(
                f"""
                Port 22
                AddressFamily any
                ListenAddress 0.0.0.0
                ListenAddress ::
                PermitRootLogin yes
                LogLevel INFO
                AuthorizedKeysFile "{CONFIG.io_dir}/authorized_keys"
                PasswordAuthentication no
                """
                """
                StrictModes no
                """  # 关闭 authorized_keys 文件和其所在目录的权限检查
                """
                KbdInteractiveAuthentication no
                AcceptEnv LANG LC_*
                Subsystem sftp /usr/lib/openssh/sftp-server
                """
            )
        )
    return path


# ==================================================================================== #
if __name__ == "__main__":
    try:
        import coverage

        coverage.process_startup()
    except ImportError:
        pass

    from base import RUNNER

    RUNNER.run(entry.main(start, stop, "YatCC-SE", CONFIG.log_dir, CONFIG.log_level))
