"""容器初始程序框架"""

import asyncio as aio
import os
import signal
from typing import Coroutine, Callable

from . import Path_t, logger
from .progress import PROGRESS, PrintOut, TimeTree

LOGGER: logger.Logger
_EXIT_CODE: int | None

Callback_t = Callable[[], Coroutine[None, None, None]]
_START_CALLBACK: Callback_t
_STOP_CALLBACK: Callback_t


def terminate(code=0):
    """在协程中调用，主动终止系统"""

    global _EXIT_CODE, _FOREVER_TASK, _FOREVER_EVENT
    if _EXIT_CODE is not None:
        return  # 防止重复调用
    _EXIT_CODE = code
    # 取消所有当前任务，尽快恢复执行 _forever() 协程
    cur_task = aio.current_task()
    for task in aio.all_tasks():
        if task is not cur_task and task is not _FOREVER_TASK:
            LOGGER.notice("CANCEL %r", task)
            task.cancel()
    _FOREVER_EVENT.set()


def _reapchld():
    """SIGCHLD 信号处理函数，尝试回收所有子进程"""

    while True:
        try:
            pid, code = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                break
            if os.WIFEXITED(code):
                exitinfo = f"正常退出，退出码 {os.WEXITSTATUS(code)}"
            else:
                exitinfo = f"异常终止，退出信号 {os.WTERMSIG(code)}"
            PROGRESS(f"已回收子进程 {pid}: {exitinfo}", logger=LOGGER)
        except ChildProcessError:
            break


async def _forever():
    global _FOREVER_TASK, _FOREVER_EVENT
    _FOREVER_TASK = aio.current_task()
    _FOREVER_EVENT = aio.Event()

    # 避免在启动过程中被信号打断
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    PROGRESS.push(TimeTree(flush=True))
    with PROGRESS["开始启动系统", LOGGER]:
        try:
            await _START_CALLBACK()
        except BaseException:
            LOGGER.fatal(PROGRESS("启动系统失败"), exc_info=True)
            return
        PROGRESS("启动系统完成", logger=LOGGER)
    PROGRESS.pop()
    PROGRESS(
        "\n"
        "==========================\n"
        ">>>>> SYSTEM STARTED <<<<<\n"
        "==========================\n",
    )

    loop = aio.get_event_loop()
    loop.add_signal_handler(signal.SIGCHLD, _reapchld)
    loop.add_signal_handler(signal.SIGTERM, terminate)
    loop.add_signal_handler(signal.SIGINT, terminate)

    # 等待 terminate() 被调用，然后优雅退出
    await _FOREVER_EVENT.wait()
    PROGRESS("\n收到信号，退出系统")
    PROGRESS.push(TimeTree(flush=True))
    with PROGRESS["开始停止系统", LOGGER]:
        try:
            await _STOP_CALLBACK()
        except BaseException:
            LOGGER.fatal(PROGRESS("停止系统失败"), exc_info=True)
            return
        PROGRESS("停止系统完成", logger=LOGGER)
    PROGRESS.pop()
    PROGRESS(
        "\n"
        "==========================\n"
        ">>>>> SYSTEM STOPPED <<<<<\n"
        "==========================\n",
    )


async def main(
    start_cb: Callback_t,
    stop_cb: Callback_t,
    log_name: str,
    log_dir: Path_t,
    log_level=logger.INFO,
) -> int:
    """入口主函数

    :param start_cb: 启动时的异步回调
    :param stop_cb: 停止时的异步回调
    :param log_name: 日志文件名
    :param log_dir: 日志目录路径，会在其下创建以启动时间命名的子目录
    :param log_dir_env: 日志路径环境变量名，如果不为 None 则优先使用环境变量中的值
    :param log_level: 默认日志级别
    :return: 退出码
    """

    PROGRESS.push(PrintOut(flush=True))
    PROGRESS(log_dir)
    PROGRESS(log_dir)
    PROGRESS(log_dir)

    global LOGGER, _EXIT_CODE, _START_CALLBACK, _STOP_CALLBACK
    from .logger import setup_logger, logger

    _START_CALLBACK, _STOP_CALLBACK = start_cb, stop_cb
    setup_logger(log_dir, log_name, unilog=True, level=log_level)
    LOGGER = logger(__spec__, __file__)
    # 在初始化日志模块后再创建 LOGGER，以便使用 log_dir

    _EXIT_CODE = None
    await _forever()
    if _EXIT_CODE is None:
        PROGRESS("退出码未设置，很可能未使用 terminate() ！", logger=LOGGER.warning)
        _EXIT_CODE = -1
    return _EXIT_CODE


# ==================================================================================== #


async def start_subp(
    logger: logger.Logger,
    *cmd: str,
    stdout: str | None = None,
    stderr: str | None = None,
    **kwargs,
) -> aio.subprocess.Process:
    from shlex import quote

    logger.notice(
        "%s\n" "stdout: %r\n" "stderr: %r\n" "%r",
        " ".join(map(quote, cmd)),
        stdout,
        stderr,
        kwargs,
    )

    stdout = stdout or str(logger.unipath(suffix=".out"))
    os.makedirs(os.path.dirname(stdout), exist_ok=True)

    stderr = stderr or str(logger.unipath(suffix=".err"))
    os.makedirs(os.path.dirname(stderr), exist_ok=True)

    with open(stdout, "wb") as out, open(stderr, "wb") as err:
        ret = await aio.create_subprocess_exec(
            *cmd,
            stdin=aio.subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,  # 将子进程放入新的进程组，避免收到当前进程的信号
            **kwargs,
        )
    return ret


async def stop_subp(
    ps: aio.subprocess.Process,
    signal=signal.SIGTERM,
    timeout: float | None = None,
) -> tuple[bool, int]:
    try:
        try:
            ps.send_signal(signal)
            code = await aio.wait_for(ps.wait(), timeout)
            return True, code
        except aio.TimeoutError:
            ps.kill()
            code = await ps.wait()
            return False, code
    except Exception:
        global LOGGER
        LOGGER.error("停止子进程 %r 失败", ps, exc_info=True)
        return False, -1
