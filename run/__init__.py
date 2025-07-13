import asyncio as aio
import os
import shlex
import subprocess as subp
from contextlib import nullcontext
from datetime import datetime

import cluster
from base import PROJECT_DIR, Path, Path_t, guard_once
from base.logger import INFO, Logger
from base.run import Prologue_t, prologue
from config import ENVIRON

RUNNING_DIR: Path
"""运行时目录"""
INDEX_LOGGER: Logger
"""主索引日志器"""


def __run__(_spec_, _file_, level=1, time_tree=True) -> Prologue_t:
    global RUNNING_DIR, INDEX_LOGGER
    RUNNING_DIR, INDEX_LOGGER, progress = prologue(
        _spec_,
        _file_,
        PROJECT_DIR / "scripts",
        PROJECT_DIR / "running",
        level=level,
        time_tree=time_tree,
    )
    return RUNNING_DIR, INDEX_LOGGER, progress


@guard_once
async def ainit_cluster() -> cluster.ClusterABC:
    global CLUSTER
    from cluster import create

    CLUSTER = create(
        mock=ENVIRON.mock_cluster,
    )

    return CLUSTER


# ==================================================================================== #


class RunFailed(Exception):
    """运行失败"""


async def arun(
    cmd: Path_t,
    *args: Path_t,
    cwd: Path_t | None = None,
    env: dict[str, Path_t] = {},
    stdin: Path_t | None = None,
    stdout: Path_t | None = None,
    stderr: Path_t | None = None,
    envs: dict[str, Path_t] | None = None,
    level=INFO,
    check: int | None = None,
    stacklevel=2,
) -> tuple[Path, Path, int]:
    """异步运行子进程，同时记录日志

    :param cmd: 命令
    :param args: 参数
    :param cwd: 工作目录，默认使用自动路径
    :param env: 额外的环境变量
    :param stdin: 标准输入重定向，None 使用 /dev/null
    :param stdout: 标准输出重定向，None 时使用自动路径
    :param stderr: 标准错误输出重定向，None 时使用自动路径
    :param envs: 完整的环境变量，默认使用 os.environ
    :param level: 日志级别，默认 INFO
    :param check: 检查返回码为指定的值，默认不检查
    :return: 标准输出文件路径，标准错误文件路径，返回码
    """

    from . import INDEX_LOGGER

    unipath = INDEX_LOGGER.unipath(".run")
    unipath_mkdir = False

    command = [str(cmd), *map(str, args)]
    if cwd is None:
        unipath_mkdir = True
        cwd = unipath

    if envs is None:
        environ = {k: str(v) for k, v in os.environ.items()}
    else:
        environ = {k: str(v) for k, v in envs.items()}
    env_str = {k: str(v) for k, v in env.items()}
    environ.update(env_str)

    if stdout is None:
        unipath_mkdir = True
        stdout = unipath / "stdout"
    if stderr is None:
        unipath_mkdir = True
        stderr = unipath / "stderr"

    if unipath_mkdir:
        unipath.mkdir(parents=True, exist_ok=True)
    with open(stdout, "wb") as out, open(stderr, "wb") as err:
        with open(stdin, "rb") if stdin else nullcontext(subp.DEVNULL) as in_:
            timing = datetime.now()
            if v := os.getenv("BASE_ARUN_DRY"):
                returncode = int(v)
            else:
                ps = await aio.create_subprocess_exec(
                    cmd,
                    *args,
                    cwd=str(cwd),
                    env=environ,
                    stdin=in_,
                    stdout=out,
                    stderr=err,
                )
                returncode = await ps.wait()
            timing_cost = datetime.now() - timing

    INDEX_LOGGER.log(
        level,
        "RUN: %s\nCWD: %s\nIN_: %s\nOUT: %s\nERR: %s\nENV: %s\nRET: %s\n(%s)",
        shlex.join(command),
        cwd,
        stdin,
        stdout,
        stderr,
        env_str if envs is None else environ,
        returncode,
        timing_cost,
        stacklevel=stacklevel,
    )

    if check is not None and check != returncode:
        raise RunFailed(returncode, command)
    return Path(stdout), Path(stderr), returncode
