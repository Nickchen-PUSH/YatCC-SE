"""采用定制风格的日志系统

TODO：直接从环境变量初始化，与应用代码分离

因为全局变量有进程间穿透能力，使用 logger 模块的脚本中无需编写
特殊的初始化操作即可使用父进程的日志配置，体现了面向切面编程的思想。
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from io import IOBase
from pathlib import Path
from random import sample
from shutil import rmtree
from typing import Any, Generator, cast

from . import PROJECT_DIR, Path_t, timetag

INFO = logging.INFO
NOTICE = logging.INFO + 5
VERBOSE = logging.INFO - 5


class Logger(logging.Logger):

    __rel_log_dir: Path
    _Logger__rel_log_dir: Path

    @property
    def dir(self) -> Path:
        """获取对应的日志目录"""

        global _LOG_DIR
        return _LOG_DIR / self.__rel_log_dir

    def path(self, *path: Path_t, rm=False, mp=False, md=False) -> Path:
        """获取 *path 在日志目录中的绝对路径

        :param rm: 是否删除目标
        :param mp: 是否创建父目录
        :param md: 是否创建目标为目录
        :return: 绝对路径
        """

        ret = self.dir.joinpath(*path).absolute()
        if rm:
            rmtree(ret, ignore_errors=True)
        if mp:
            ret.parent.mkdir(parents=True, exist_ok=True)
        if md:
            ret.mkdir(parents=True, exist_ok=True)
        return ret

    def unipath(self, *path: Path_t, prefix="", suffix="", mp=False, md=False) -> Path:
        """获取 *path 中的一个唯一路径

        :param mp: 是否创建父目录
        :param md: 是否创建目标为目录
        :return: 绝对路径
        """

        rstr = "".join(sample("0123456789abcdefghijklmnopqrstuvwxyz", 4))
        name = prefix + timetag(us=True) + "-" + rstr + suffix
        ret = self.dir.joinpath(*path).absolute() / name
        if mp:
            ret.parent.mkdir(parents=True, exist_ok=True)
        if md:
            ret.mkdir(parents=True, exist_ok=True)
        return ret

    def notice(self, msg, *args, **kwargs):
        """输出通知级别日志"""

        if self.isEnabledFor(NOTICE):
            self._log(NOTICE, msg, args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        """输出冗余级别日志"""

        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)


class Formatter(logging.Formatter):

    def format(self, rec: logging.LogRecord) -> str:
        body = super().format(rec)

        created = datetime.fromtimestamp(rec.created)
        timestamp = created.strftime("%y-%m-%d+%H-%M-%S+%f")
        thread = rec.thread or ""
        taskName = repr(rec.taskName) if rec.taskName else ""

        head = (
            f"\n{rec.levelno} {rec.name} ["
            f"{repr(rec.pathname)}:{rec.lineno} | "
            f"{timestamp} {thread}-{taskName}"
            f"] {len(body)}\n"
        )
        return head + body


def logger(_spec_, _file_) -> Logger:
    """获取当前模块的日志记录器

    :param _spec_: 传入 __spec__ 变量
    :param _file_: 传入 __file__ 变量
    :return: 日志记录器
    """
    relpath = Path(_file_).relative_to(PROJECT_DIR)

    previous = logging.getLoggerClass()
    logging.setLoggerClass(Logger)
    if _spec_ is not None and _spec_.name != "__main__":
        name = _spec_.name
    else:
        name = str(relpath)
    ret = cast(Logger, logging.getLogger(name))
    logging.setLoggerClass(previous)

    ret._Logger__rel_log_dir = relpath
    return ret


# ==================================================================================== #


LOGGER: Logger | None = None
_LOG_DIR: Path
_LOG_INDEX: Path


def setup_logger(
    log_dir: Path_t,
    index_name: str,
    *,
    stderr=False,
    unilog=False,
    level=logging.INFO,
) -> Path:
    """初始化日志模块

    它被故意设计为同步的，且允许多次调用，后续调用会被忽略。

    :param log_dir: 日志目录
    :param index_name: 索引文件名
    :param stderr: 打印日志到标准输出，而不是重定向到文件
    :param unilog: 不向索引文件名中加入进程号，使多进程共用一个日志文件
    :param level: 初始日志级别
    :return: 索引文件名
    """
    global LOGGER, _LOG_DIR, _LOG_INDEX
    from os import getpid

    if LOGGER is not None:
        LOGGER.warning("IGNORE REINIT: %r", index_name)
        return _LOG_INDEX

    _LOG_DIR = Path(log_dir)
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    if stderr:
        handler: logging.Handler = logging.StreamHandler()
        _LOG_INDEX = Path("/dev/stderr")
    else:
        if unilog:
            _LOG_INDEX = _LOG_DIR / f"{index_name}.index"
        else:
            _LOG_INDEX = _LOG_DIR / f"{index_name}.{getpid()}.index"
        handler = logging.FileHandler(filename=_LOG_INDEX)
    handler.setFormatter(Formatter(style="{"))
    logging.root.addHandler(handler)
    logging.root.setLevel(level)

    LOGGER = logger(__spec__, __file__)
    LOGGER.log(99, "INIT WITH LEVEL %s", logging.root.level)
    return _LOG_INDEX


# ==================================================================================== #


class Parser:
    """对应于 Formatter 输出风格的日志解析器"""

    @dataclass
    class Record:
        """一条日志记录"""

        level: int
        name: str
        file: str
        line: int
        when: datetime
        thread: str
        taskName: str
        body: str

    def parse_io(self, io: IOBase) -> Generator[Any, Any, Record]:
        raise NotImplementedError("TODO")

    def parse_text(self, text: str) -> Generator[Any, Any, Record]:
        raise NotImplementedError("TODO")

    def parse_file(self, path: Path) -> Generator[Any, Any, Record]:
        raise NotImplementedError("TODO")

    def filter(self, rec: Record) -> Record | None:
        """过滤器，在子类中重写以在解析中过滤日志记录

        :param rec: 日志记录
        :return: 过滤后的日志记录，或 None 表示丢弃
        """
        return rec


