import sys

from . import Path_t, timetag
from .logger import Logger, Path
from .progress import _PROGRESS, PROGRESS

Prologue_t = tuple[Path, Logger, _PROGRESS]


def prologue(
    _spec_,
    _file_,
    root_dir: Path_t,
    running_dir: Path_t,
    level=1,
    time_tree=True,
) -> Prologue_t:
    """项目脚本的初始化引言

    :param _spec_: 传入 __spec__
    :param _file_: 传入 __file__
    :param root_dir: 脚本集的根目录
    :param running_dir: 运行时目录
    :param level: 日志输出级别
    :param time_tree: 是否使用时间树进度
    :return: 返回运行目录路径、日志对象、进度对象
    """

    from atexit import register
    from datetime import datetime
    from shlex import quote

    from .logger import logger, setup_logger

    running_dir = Path(running_dir)
    running_dir.mkdir(parents=True, exist_ok=True)
    ret0 = running_dir.resolve() / Path(_file_).relative_to(root_dir)
    ret0 = ret0.absolute()

    ret1 = logger(_spec_, _file_)
    log_dir_name = timetag(datetime.now(), us=True) + "." + ret0.name
    path = quote(
        str(
            setup_logger(
                running_dir / ".log" / log_dir_name,
                ret0.name,
                unilog=True,
                level=level,
            )
        )
    )

    PROGRESS.push_PrintOut(flush=True)
    PROGRESS(path)
    PROGRESS(path)
    PROGRESS(path)
    if time_tree:
        PROGRESS.push_TimeTree(flush=True)
        register(PROGRESS.pop)

    ret1.info("%r", sys.argv)
    return ret0, ret1, PROGRESS
