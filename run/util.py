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


async def npm_install(cwd: Path_t) -> None:
    """异步执行 npm install

    :param cwd: 工作目录
    :param kwargs: 其他参数，参见 arun
    """

    await arun(
        ENVIRON.EXECUTABLE.npm,
        "install",
        cwd=cwd,
        stacklevel=3,
        check=0,
    )


async def npm_build(cwd: Path_t, only=False) -> None:
    """异步执行 npm run build

    :param cwd: 工作目录
    :param kwargs: 其他参数，参见 arun
    """

    await arun(
        ENVIRON.EXECUTABLE.npm,
        "run",
        "build-only" if only else "build",
        cwd=cwd,
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


async def tar_cf_dir(out: Path_t, dir: Path_t) -> None:
    """异步执行 tar，将目录里的所有文件打包，但不包括目录本身

    :param out: 输出文件，必须以 .tar / .tgz / .txz 结尾
    :param dir: 目录
    :param kwargs: 其他参数，参见 arun
    """

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix == ".tar":
        opt = "-cf"
    elif out.suffix == ".tgz":
        opt = "-czf"
    elif out.suffix == ".txz":
        opt = "-cJf"
    else:
        raise ValueError(f"不支持的输出文件类型：{out!r}")
    await arun(
        ENVIRON.EXECUTABLE.tar,
        *[opt, str(out)],
        *["-C", str(dir)],
        ".",
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
