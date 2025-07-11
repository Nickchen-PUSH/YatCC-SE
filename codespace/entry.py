#!/usr/bin/env python3
"""代码空间容器入口，同时也是监控鼹鼠"""

import asyncio as aio
import os
import shutil
import sys

from base import entry
from base.logger import logger
from base.progress import PROGRESS

from . import CONFIG

LOGGER = logger(__spec__, __file__)

SSH_SERVER: aio.subprocess.Process | None
CODE_SERVER: aio.subprocess.Process
CENTRAL_CONTROL: str | None
STUDENT_API_KEY: str | None
HTTP_PROXY: str | None
KEEPALIVE_INTERVAL: float


async def start() -> None:
    assert CONFIG.log_dir.endswith("/")

    ######
    os.makedirs(CONFIG.log_dir, exist_ok=True)
    CONFIG.markdown(CONFIG.log_dir + "config.md")

    ######
    with PROGRESS["初始化环境变量", LOGGER]:
        # global CENTRAL_CONTROL
        # ek = "CENTRAL_CONTROL"
        # PROGRESS(ek + " ... ")
        # CENTRAL_CONTROL = os.getenv(ek)
        # PROGRESS(f"{CENTRAL_CONTROL=}", logger=LOGGER)
        # PROGRESS("NOT SET" if CENTRAL_CONTROL is None else "OK")

        ######
        global STUDENT_API_KEY
        ek = "STUDENT_API_KEY"
        PROGRESS(ek + " ... ")
        STUDENT_API_KEY = os.getenv(ek)
        PROGRESS(f"{STUDENT_API_KEY=}", logger=LOGGER)
        PROGRESS("NOT SET" if STUDENT_API_KEY is None else "OK")

        #####
        # global HTTP_PROXY
        # ek = "HTTP_PROXY"
        # PROGRESS(ek + " ... ")
        # HTTP_PROXY = os.getenv(ek)
        # PROGRESS(f"{HTTP_PROXY=}", logger=LOGGER)
        # PROGRESS("NOT SET" if HTTP_PROXY is None else "OK")

        ######
        # global KEEPALIVE_INTERVAL
        # ek = "YatCC_KEEPALIVE_INTERVAL"
        # PROGRESS(ek + " ... ")
        # if (x := os.getenv(ek)) is None:
        #     KEEPALIVE_INTERVAL = float(60 * 5)
        #     PROGRESS(f"NOT SET -> {KEEPALIVE_INTERVAL}")
        # else:
        #     try:
        #         KEEPALIVE_INTERVAL = float(x)
        #         PROGRESS(f"{x!r} -> {KEEPALIVE_INTERVAL}")
        #     except ValueError:
        #         PROGRESS("KEEPALIVE_INTERVAL 环境变量不是数值", logger=LOGGER)
        #         PROGRESS("NOT A NUMBER")
        #         return
        # PROGRESS(f"{KEEPALIVE_INTERVAL=} ({x!r})", logger=LOGGER)

    ######
    global SSH_SERVER
    if not CONFIG.ENTRY.sshd_executable:
        SSH_SERVER = None
        PROGRESS("SSH 服务已禁用", logger=LOGGER)
    else:
        with PROGRESS["启动 SSH 服务", LOGGER]:
            os.makedirs(
                "/run/sshd", exist_ok=True
            )  # sshd 需要 /run/sshd 目录来权限分离

            ssh_log = CONFIG.log_dir + "sshd.log"
            os.mknod(
                rmfile(ssh_log), 0o644
            )  # 允许其它用户读取日志，sshd 创建的默认是 600 权限

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
    global CODE_SERVER
    with PROGRESS["启动 Code Server", LOGGER]:
        code_server_path = shutil.which("code-server")
        if code_server_path is None:
            PROGRESS("找不到 code-server 命令", logger=LOGGER)
            raise RuntimeError("找不到 code-server 命令")

        os.makedirs("/io/code-user-data", exist_ok=True)
        CODE_SERVER = await entry.start_subp(
            LOGGER,
            code_server_path,
            "/code",
            *["--bind-addr", "0.0.0.0:443"],
            *(["--auth", "password"] if STUDENT_API_KEY else ["--auth", "none"]),
            "--disable-update-check",
            "--disable-workspace-trust",
            *["--locale", "zh-Hans"],
            *["--user-data-dir", "/io/code-user-data"],
            *["--extensions-dir", "/app/code-extensions"],
            stdout=CONFIG.log_dir + "code-server.stdout.start",
            stderr=CONFIG.log_dir + "code-server.stderr.start",
            env={
                **os.environ,
                **({"PASSWORD": STUDENT_API_KEY} if STUDENT_API_KEY else {}),
            },
        )
        PROGRESS(f"PID: {CODE_SERVER.pid}")

    ######
    aio.create_task(run(), name="run")


async def stop():
    """停止系统时执行（优雅退出）"""

    ######
    global CODE_SERVER
    with PROGRESS["停止 Code Server", LOGGER]:
        code_ok, code_res = await entry.stop_subp(CODE_SERVER, timeout=3)
        if not code_ok or code_res != 0:
            PROGRESS(f"Code Server 异常退出，退出码 {code_res}", logger=LOGGER)

    ######
    global SSH_SERVER
    if SSH_SERVER is not None:
        with PROGRESS["停止 SSH 服务", LOGGER]:
            ssh_ok, ssh_res = await entry.stop_subp(SSH_SERVER, timeout=1)
            if not ssh_ok or ssh_res != 0:
                PROGRESS(f"SSH 服务异常退出，退出码 {ssh_res}", logger=LOGGER)


async def run():
    """在系统运行期间执行"""

    global CENTRAL_CONTROL
    global STUDENT_API_KEY
    global HTTP_PROXY
    global KEEPALIVE_INTERVAL
    global CODE_SERVER
    if CENTRAL_CONTROL is None:
        PROGRESS("自动保活已禁用", logger=LOGGER)
        return

    while True:
        await aio.sleep(KEEPALIVE_INTERVAL)

        if CODE_SERVER.returncode is not None:
            PROGRESS(
                f"Code Server 已退出，退出码 {CODE_SERVER.returncode}", logger=LOGGER
            )
            PROGRESS(f"因 Code Server 退出而终止，退出码 {CODE_SERVER.returncode}")
            entry.terminate(CODE_SERVER.returncode)
            break

        # PROGRESS("运行监控鼹鼠进行保活")
        # with open(CONFIG.log_dir + "mole.out", "ab") as out, open(
        #     CONFIG.log_dir + "mole.err", "ab"
        # ) as err:
        #     mole_proc = await aio.create_subprocess_exec(
        #         sys.executable,
        #         *["-m", "yatcc_cs.mole"],
        #         *["--central-control", CENTRAL_CONTROL],
        #         *["--student-api-key", STUDENT_API_KEY],
        #         *["--http-proxy", HTTP_PROXY],
        #         cwd=CONFIG.app_dir,
        #         stdin=aio.subprocess.DEVNULL,
        #         stdout=out,
        #         stderr=err,
        #     )
        # if mole_proc.returncode != 0:
        #     PROGRESS(f"监控鼹鼠异常退出，退出码 {mole_proc.returncode}", logger=LOGGER)


# ==================================================================================== #
from textwrap import dedent


def rmfile(path: str) -> str:
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
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
    from base import RUNNER

    RUNNER.run(entry.main(start, stop, "CODESPACE", CONFIG.log_dir, CONFIG.log_level))
