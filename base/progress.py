import sys
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from typing import Any, Iterable, Callable, AsyncIterable, overload
from types import EllipsisType, NotImplementedType


class Progress:
    """进度监控接口基类，也是空监控器的默认实现"""

    _Progress__prev: "Progress"

    def __init__(self):
        self.__prev = self

    def desc(self, msg: Any = None) -> None:
        """描述当前状态

        :param msg: 提示消息，None 指代空消息
        """

    def total(
        self, num: int | EllipsisType | None = None, msg: Any | None = None
    ) -> None:
        """设置进度总量

        :param num: 进度总量，Ellipsis(...) 指代未知，None 取消设置总量
        :param msg: 提示消息，None 指代空消息
        """

    def step(self, rel: int, msg: Any | None = None) -> None:
        """将进度推进一个相对值 rel

        :param rel: 推进的相对值
        :param msg: 提示消息，None 指代空消息
        """

    def jump(self, abs: int, msg: Any | None = None) -> None:
        """将进度跳到一个绝对值 abs

        :param abs: 跳到的绝对值
        :param msg: 提示消息，None 指代空消息
        """

    def enter(self, msg: Any = None) -> None:
        """进入子过程

        :param msg: 提示消息，None 指代空消息
        """

    def exit(self, exc: Exception | None = None) -> None:
        """退出子过程

        :param msg: 提示消息，None 指代空消息
        :param exc: 如果因异常退出则为异常对象
        """

    def pushed(self) -> None:
        """进度监视器被 push 时调用"""

    def popped(self) -> None:
        """进度监视器被 pop 时调用"""


# ==================================================================================== #


class _PROGRESS(Progress):

    def __init__(self) -> None:
        self._cur: Progress = self

    @staticmethod
    def push(pr: Progress) -> None:
        """使用新的局部进度监视器 pr

        进度监视器同一时刻只能被 push 一次，在 pop 前不能被重复使用！

        :param pr: 进度监视器实例
        """

        assert pr._Progress__prev is pr, "progress already pushed"
        pr._Progress__prev = PROGRESS._cur
        PROGRESS._cur = pr
        pr.pushed()

    @staticmethod
    def pop() -> Progress | None:
        """恢复到上一个局部进度监视器

        在顶级进度监视器上调用 pop 会被忽略，因此是安全的。

        :return: 返回被 pop 的进度监视器，如果已经到达顶级则返回 None
        """

        cur = PROGRESS._cur
        prev = PROGRESS._cur._Progress__prev
        if cur is prev:
            return None
        cur._Progress__prev = cur
        PROGRESS._cur = prev
        cur.popped()
        return cur

    @staticmethod
    def push_PrintOut(**kwargs) -> None:
        """使用 PrintOut 进度监视器"""

        PROGRESS.push(PrintOut(**kwargs))

    @staticmethod
    def push_TimeTree(out=sys.stderr, flush=False) -> None:
        """使用 TimeTree 进度监视器"""

        PROGRESS.push(TimeTree(out, flush))

    # ============================================================================ #

    @staticmethod
    def __call__(
        msg: Any | None = None,
        total: int | EllipsisType | None | NotImplementedType = NotImplemented,
        logger: Logger | Callable | None = None,
    ) -> Any:
        """圆括号（调用）语法提示状态和进度总量

        ```
        PROGRESS("msg")                 # 提示状态
        PROGRESS("msg", 100)            # 提示状态，同时设置进度总量
        PROGRESS("msg", logger=LOGGER)  # 提示状态，同时记录日志
        PROGRESS(total=None)            # 设置进度总量为未知
        PROGRESS("msg", 100, LOGGER)    # 完全形式
        ```

        :param msg: 提示消息，None 指代空消息
        :param total: 进度总量，Ellipsis(...) 指代未知，None 取消设置总量
        :param logger: 日志记录器
        :return: 返回 msg
        """

        if logger is not None:
            if isinstance(logger, Logger):
                logger.info(
                    "PROGRESS (%s)\n%s",
                    "..." if total is ... else total,
                    msg,
                    stacklevel=2,
                )
            else:
                logger("PROGRESS (%s)\n%s", total, msg, stacklevel=2)
        if total is not NotImplemented:
            PROGRESS._cur.total(total, msg)
        else:
            PROGRESS._cur.desc(msg)
        return msg

    @staticmethod
    def __enter__() -> "_PROGRESS":
        """使用空消息进入子过程"""

        PROGRESS._cur.enter()
        return PROGRESS

    @staticmethod
    def __exit__(exc_type, exc_value, traceback) -> None:
        PROGRESS._cur.exit(exc_value)

    class WithEnter:

        def __init__(self, msg) -> None:
            self.msg = msg

        def __enter__(self):
            PROGRESS._cur.enter(self.msg)
            del self.msg  # 尽早释放资源
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            PROGRESS._cur.exit(exc_value)

    @staticmethod
    def __getitem__(
        arg: tuple[Any | None, Logger | Callable] | Any,
    ) -> "_PROGRESS.WithEnter":
        """方括号语法语法进入子过程

        ```
        with PROGRESS["msg"]:           # 同时提示状态
        with PROGRESS["msg", LOGGER]:   # 同时提示状态和记录日志
        ```
        """

        if type(arg) is tuple:
            msg, logger = arg
        else:
            msg, logger = arg, None
        if logger is not None:
            if isinstance(logger, Logger):
                logger.info("PROGRESS ENTER\n%s", msg, stacklevel=2)
            else:
                logger("PROGRESS ENTER\n%s", msg, stacklevel=2)
        return _PROGRESS.WithEnter(msg)

    def __add__(self, rel: int | tuple[str, int]) -> "_PROGRESS":
        """加运算符 + 用于步进进度

        ```
        PROGRESS + 3   # 步进 3
        PROGRESS + ("msg", 3)  # 步进 3，同时提示状态
        ```

        :param msg: 提示消息
        """

        if type(rel) is tuple:
            msg, rel = rel
            PROGRESS._cur.step(rel, msg)
        elif type(rel) is int:
            PROGRESS._cur.step(rel)
        else:
            raise TypeError(rel)
        return PROGRESS

    def __iadd__(self, abs: int | tuple[str, int]) -> "_PROGRESS":
        """加等于运算符 += 用于跳到进度

        ```
        PROGRESS += 10  # 跳到 10
        PROGRESS += ("msg", 10)  # 跳到 10，同时提示状态
        ```
        """

        if type(abs) is tuple:
            msg, abs = abs
            PROGRESS._cur.jump(abs, msg)
        elif type(abs) is int:
            PROGRESS._cur.jump(abs)
        else:
            raise TypeError(abs)
        return PROGRESS

    class ForIter:

        def __init__(self, seq: Iterable) -> None:
            self.seq = seq

        def __iter__(self):
            self.it = self.seq.__iter__()
            del self.seq  # 尽早释放资源
            return self

        def __next__(self):
            i = self.it.__next__()
            PROGRESS._cur.step(1)
            return i

        def __aiter__(self):
            self.ait = self.seq.__aiter__()
            del self.seq
            return self

        async def __anext__(self):
            i = await self.ait.__anext__()
            PROGRESS._cur.step(1)
            return i

    def __matmul__[T](self, seq: Iterable[T]) -> Iterable[T]:
        """矩阵乘法运算符 @ 用于包装迭代器

        ```
        for i in PROGRESS @ range(100):
        ```

        :param seq: 可迭代对象
        :return: 迭代器
        """

        self._cur.total(
            len(seq) if hasattr(seq, "__len__") else None,  # type: ignore
            f"@{type(seq).__name__}<{id(seq)}>",
        )
        return _PROGRESS.ForIter(seq)

    @overload
    def __mod__[T](self, seq: Iterable[T]) -> Iterable[T]: ...

    @overload
    def __mod__[T](self, seq: AsyncIterable[T]) -> AsyncIterable[T]: ...

    def __mod__(self, seq):
        """取模运算符 % 用于包装迭代器，但是不自动设置总量

        ```
        for i in PROGRESS % range(100):
        ```

        :param seq: 可迭代对象
        :return: 迭代器
        """

        return _PROGRESS.ForIter(seq)


PROGRESS = _PROGRESS()
"""全局进度监视器，面向用户的进度监视服务点"""


# ==================================================================================== #


Silence = Progress


class PrintOut(Progress):
    """简单地调用 print() 输出进度信息"""

    def __init__(self, file=sys.stderr, **kwargs):
        super().__init__()
        self.kwargs = {"file": file, **kwargs}

    def desc(self, msg: Any = None) -> None:
        print(msg, **self.kwargs)

    def total(
        self, total: int | EllipsisType | None = None, msg: Any | None = None
    ) -> None:
        print(f"</{'...' if total is ... else total}>", msg, **self.kwargs)

    def step(self, rel: int, msg: Any | None = None) -> None:
        print(f"<+{rel}/>", msg, **self.kwargs)

    def jump(self, abs: int, msg: Any | None = None) -> None:
        print(f"<{abs}/>", msg, **self.kwargs)

    def enter(self, msg: Any = None) -> None:
        print(">>>", msg, **self.kwargs)

    def exit(self, exc: Exception | None = None) -> None:
        print("<<<", exc, **self.kwargs)


class TimeTree(Progress):
    """使用 print() 打印输出进度信息"""

    @dataclass
    class StackFrame:
        start_time: datetime
        last_time: datetime
        total: int | EllipsisType = ...
        current: int | None = None

    def __init__(self, out=sys.stderr, flush=False) -> None:
        super().__init__()
        self.out = out
        self.flush = flush
        self.stack = list[TimeTree.StackFrame]()

    _TIME_TAG_WIDTH = 6

    @staticmethod
    def __time_tag(seconds: float) -> str:
        width = TimeTree._TIME_TAG_WIDTH

        s = f"{seconds:.2f}".rstrip("0").rstrip(".")
        if len(s) <= width:
            return s.rjust(width)

        minute = seconds / 60
        s = f"{minute:.2f}".rstrip("0").rstrip(".") + "m"
        if len(s) <= width:
            return s.rjust(width)

        hour = minute / 60
        s = f"{hour:.2f}".rstrip("0").rstrip(".") + "h"
        if len(s) <= width:
            return s.rjust(width)

        day = hour / 24
        s = f"{day:.2f}".rstrip("0").rstrip(".") + "d"
        if len(s) <= width:
            return s.rjust(width)

        return "*" * width

    def __indent(self) -> str:
        assert self.stack
        frame = self.stack[-1]

        now = datetime.now()
        time_tag = self.__time_tag((now - frame.last_time).total_seconds())
        frame.last_time = now

        level = len(self.stack)
        return time_tag + " |" * level

    def __indent_lines(self, text: str) -> str | None:
        width = TimeTree._TIME_TAG_WIDTH

        lines = text.split("\n")
        if len(lines) == 1:
            return None
        prefix = "\n" + " " * width + " |" * len(self.stack) + "  "
        return prefix + prefix.join(lines) + prefix  # 换行开头，结尾无换行

    def __message(self, msg) -> str:
        assert self.stack
        frame = self.stack[-1]

        text = str("" if msg is None else msg)
        text = self.__indent_lines(text) or text

        first_line = self.__indent()
        if frame.current is None:
            first_line += "- "
        elif frame.total is ...:
            first_line += "-[" + str(frame.current) + "] "
        else:
            total = str(frame.total)
            current = str(frame.current).rjust(len(total), ",")
            first_line += f"-[{current}/{total}] "

        return first_line + text + "\n"

    def __print(self, txt: str) -> None:
        self.out.write(txt)
        if self.flush:
            self.out.flush()

    def desc(self, msg: Any = None) -> None:
        if not self.stack:
            self.__print(f"{msg}\n")
            return
        self.__print(self.__message(msg))

    def total(
        self, total: int | EllipsisType | None = None, msg: Any | None = None
    ) -> None:
        if not self.stack:
            self.__print(f"</{total}> {msg}\n")
            return

        frame = self.stack[-1]
        if total is None:
            frame.total = ...
            frame.current = None
        else:
            frame.total = total
            frame.current = 0
        self.desc(msg)

    def step(self, rel: int, msg: Any | None = None) -> None:
        if not self.stack:
            self.__print(f"<+{rel}/> {msg}\n")
            return

        frame = self.stack[-1]
        frame.current = (frame.current or 0) + rel
        self.desc(msg)

    def jump(self, abs: int, msg: Any | None = None) -> None:
        if not self.stack:
            self.__print(f"<{abs}/> {msg}\n")
            return

        frame = self.stack[-1]
        frame.current = abs
        self.desc(msg)

    def enter(self, msg: Any = None) -> None:
        if not self.stack:
            self.__print("-" * (TimeTree._TIME_TAG_WIDTH + 2) + "\n")
        first_line = self.__indent() + "--- "

        now = datetime.now()
        frame = TimeTree.StackFrame(now, now)
        self.stack.append(frame)

        text = str(msg or "")
        text = self.__indent_lines(text) or text

        self.__print(first_line + text + "\n")

    def exit(self, exc: Exception | None = None) -> None:
        assert self.stack
        frame = self.stack.pop()

        level = len(self.stack)
        indent = " " * TimeTree._TIME_TAG_WIDTH + " |" * level
        time_cost = str(datetime.now() - frame.start_time)
        line = indent + " \\" + time_cost + "/"
        if exc is not None:
            line += " " + type(exc).__name__
        self.__print(line + "\n")

    def pushed(self) -> None:
        self.__print("-" * (TimeTree._TIME_TAG_WIDTH + 2) + "\n")
        now = datetime.now()
        self.stack.append(TimeTree.StackFrame(now, now))

    def popped(self):
        self.__print("-" * (TimeTree._TIME_TAG_WIDTH + 2) + "\n")
        self.stack.clear()


# TODO 添加一个使用 ANSI 转义字符的输出实现，PrintOut 的输出实在有些不堪入目


if __name__ == "__main__":
    import time
    from logging import basicConfig, getLogger

    LOGGER = getLogger(__name__)

    basicConfig(level=1)
    PROGRESS.push(PrintOut())
    PROGRESS.push(TimeTree())

    PROGRESS("line 1\nline 2\nline 3")
    time.sleep(0.5)

    with PROGRESS["routine 1", LOGGER]:
        PROGRESS(total=3)

        time.sleep(0.5)
        PROGRESS("line 1")
        PROGRESS + 1

        time.sleep(0.5)
        PROGRESS("line 1\nline 2")
        PROGRESS + 1

        time.sleep(0.5)
        PROGRESS("line 1\nline 2\nline 3", 10, LOGGER)
        PROGRESS + 1

        PROGRESS + 3 + ("6", 3)
        PROGRESS += ("3", 3)

        with PROGRESS:
            PROGRESS(total=...)

            time.sleep(0.5)
            PROGRESS + ("state 4", 1)

            time.sleep(0.5)
            time.sleep(0.5)
            PROGRESS + ("state 5", 1) + ("state 6", 1)

        try:
            with PROGRESS["exceptions"]:
                raise ValueError("value error")
        except ValueError:
            pass

    with PROGRESS["routine 2"]:
        for i in PROGRESS @ list(range(5)):
            time.sleep(0.5)
            if i % 3 == 0:
                PROGRESS(f"state {i}")

        for i in PROGRESS % range(5):
            time.sleep(0.5)
            if i % 3 == 0:
                PROGRESS(f"state {i}")

    PROGRESS.pop()
