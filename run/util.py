

from pathlib import Path
from typing import Union
from run import arun
from config import ENVIRON


Path_t = Union[str, Path]
async def docker_build(tag: str, dir: Path_t, file: Path_t | None = None) -> None:
    if file:
        file = Path(file).relative_to(dir)
    await arun(
        ENVIRON.EXECUTABLE.docker,
        "build",
        *["-t", tag],
        *(["-f", str(file)] if file else []),
        dir,
        cwd=dir,
        stacklevel=3,
        check=0,
    )

async def rm_rf(*dst: Path_t) -> None:
    """异步执行 rm -rf

    :param dst: 目标目录
    """

    await arun(
        ENVIRON.EXECUTABLE.rm,
        "-rf",
        *map(str, dst),
        stacklevel=3,
        check=0,
    )

async def cp_rf(dst: Path_t, src: Path_t) -> None:
    """异步执行 cp -rf

    :param dst: 目标目录
    :param src: 源目录
    """

    await arun(
        ENVIRON.EXECUTABLE.cp,
        "-rf",
        str(src),
        str(dst),
        stacklevel=3,
        check=0,
    )

async def wget(url: str, out: Path_t) -> None:
    """异步执行 wget

    :param url: 下载链接
    :param out: 输出文件
    """

    await arun(
        ENVIRON.EXECUTABLE.wget,
        "-c",
        *["-O", str(out)],
        url,
        stacklevel=3,
        check=0,
    )
