"""通用基础模块

该模块中的子模块要保证提供可按需裁剪的额能力，因此 __init__.py
中不应包含除标准库以外的任何依赖。
"""

import asyncio as aio
import functools
import inspect
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union, cast

Path_t = Union[str, Path]
PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))


def timetag(dt: datetime | None = None, us=False) -> str:
    """时间标签，由数字和加减号组成，可读性高，主要用于文件名等

    :param dt: 时间对象，默认使用当前的 UTC 时间
    :param us: 是否包含微秒
    :return: 形如 `2025-03-01+07-52-02+660984+Z`
    """

    if dt is None:
        dt = datetime.now(timezone.utc)
        suffix = "+Z"
    else:
        suffix = ""
    fmt = "%Y-%m-%d+%H-%M-%S"
    if us:
        fmt += "+%f"
    fmt += suffix
    return dt.strftime(fmt)


def timetag_short(dt: datetime | None = None, us=False) -> str:
    """短时间标签，由数字和字母组成，兼容性更好

    :param dt: 时间对象，默认使用当前的 UTC 时间
    :param us: 是否包含微秒
    :return: 形如 `20250301T102204Z094879`
    """

    if dt is None:
        dt = datetime.now(timezone.utc)
        fmt = "%Y%m%dT%H%M%SZ"
    else:
        fmt = "%Y%m%dT%H%M%SH"
    if us:
        fmt += "%f"
    return dt.strftime(fmt)


PROJECT_VER = os.getenv("YatCC_OL_VERSION")
if PROJECT_VER is None:
    PROJECT_VER = timetag_short()
    os.environ["YatCC_OL_VERSION"] = PROJECT_VER


# ==================================================================================== #


class Configuration:

    @classmethod
    def overlay(cls, other: type["Configuration"]) -> type["Configuration"]:
        """配置覆盖，会递归地覆盖子配置成员。

        :param other: 另一个 Configuration 对象
        :return: 返回自身，用于链式调用
        """

        assert issubclass(other, Configuration)
        for k, v in cls.__dict__.items():
            if k.startswith("_") or not hasattr(other, k):
                continue
            attr = getattr(other, k)
            if isinstance(v, type) and issubclass(v, Configuration):
                v.overlay(attr)
            else:
                setattr(cls, k, attr)
        return cls

    @classmethod
    def markdown(cls, path: Path_t) -> None:
        """保存配置到 Markdown 文件

        :param path: 文件路径
        """

        with open(path, "w") as f:

            def markdown(cls: type[Configuration], level):
                subconfs = []

                f.write("\n" + "#" * level + f" {cls.__name__}\n\n")
                for k, v in cls.__dict__.items():
                    if k.startswith("_"):
                        continue
                    if isinstance(v, type) and issubclass(v, Configuration):
                        subconfs.append(v)
                        f.write(f"- `{k}` [{v.__name__}](#{v.__name__})\n")
                    else:
                        f.write(f"- `{k}` {v!r}\n")

                for subconf in subconfs:
                    markdown(subconf, level + 1)

            markdown(cls, 1)


# ==================================================================================== #


def guard_once[_F](f: _F) -> _F:
    """通用保护装饰器，确保函数只会被调用一次"""

    if inspect.iscoroutinefunction(f):

        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            nonlocal called, last_ret
            if called:
                return last_ret
            called = True
            last_ret = await f(*args, **kwargs)
            return last_ret

    else:

        @functools.wraps(cast(Any, f))
        def wrapper(*args, **kwargs):
            nonlocal called, last_ret
            if called:
                return last_ret
            called = True
            last_ret = f(*args, **kwargs)
            return last_ret

    called = False
    last_ret = None
    return cast(Any, wrapper)


# ==================================================================================== #


def kill_event_loop():
    """杀死当前 asyncio 事件循环中的所有任务，从而退出"""

    loop = aio.get_event_loop()
    for task in aio.all_tasks(loop):
        if task is not aio.current_task():
            task.cancel()


RUNNER = aio.Runner()
"""项目采用单线程全异步的全局代码架构，这个就是全局的异步运行器。但是，在一般情况下，应该使用
`asyncio.get_event_loop()` 来获取当前的事件循环，而不是直接使用此运行器，以避免其它模块与
base 模块耦合。"""


def guard_ainit(logger: logging.Logger | None = None):
    """保护装饰器，确保模块只会在 RUNNER 中被初始化一次

    :param logger: 日志记录器，用于记录重复初始化的警告
    """

    def decorator[_F](f: _F) -> _F:
        assert inspect.iscoroutinefunction(f), f

        @functools.wraps(f)
        async def wrapper(*args, **kwargs):
            nonlocal loop, last_ret

            if loop is None:
                loop = aio.get_event_loop()
                last_ret = await f(*args, **kwargs)
                return last_ret
            assert loop is RUNNER.get_loop(), loop
            if logger:
                logger.warning("IGNORE REINIT: %r %r", args, kwargs)
            return last_ret

        loop: aio.AbstractEventLoop | None = None
        last_ret = None
        return cast(Any, wrapper)

    return decorator
