"""项目打包工具"""

import pickle as pkl
import re as regex
import sys
import tarfile
from typing import Any, Sequence

from base import PROJECT_DIR

from . import Path, Path_t, arun


async def tar(
    out: Path_t,
    dir: Path_t,
    includes: Sequence[str] = [],
    excludes: Sequence[str] = [],
    **kwargs,
):
    """异步执行 tar，将目录里的所有文件打包，但不包括目录本身。

    正则表达式启用 DOTALL，先应用包含规则，再应用排除规则。

    :param out: 输出文件，必须以 .tar / .tgz / .txz 结尾
    :param dir: 目标打包目录
    :param includes: 包含的文件名匹配正则表达式序列
    :param excludes: 排除的文件名匹配正则表达式序列
    """
    from . import INDEX_LOGGER

    unipath = INDEX_LOGGER.unipath(".run", md=True)

    out, dir = Path(out), Path(dir).resolve()
    if out.suffix not in {".tar", ".tgz", ".txz"}:
        raise ValueError(f"不支持的输出文件类型：{out!r}")
    out.parent.mkdir(parents=True, exist_ok=True)

    if not includes:
        includes = [r".*"]
    else:
        includes = [""] + list(includes)
    inc = regex.compile("|".join(f"(?:{i})" for i in includes), regex.DOTALL)
    exc = regex.compile("|".join(f"(?:{e})" for e in excludes), regex.DOTALL)

    args = (out, dir, inc, exc)
    with open(unipath / "args", "wb") as f:
        pkl.dump(args, f)

    kwargs.setdefault("stacklevel", 3)
    ret = await arun(
        sys.executable,
        "-m",
        "run.pack",
        unipath / "args",
        cwd=PROJECT_DIR,
        stdout=unipath / "stdout",
        stderr=unipath / "stderr",
        **kwargs,
    )

    if ret[2] != 0:
        raise RuntimeError(f"打包 tar 失败（{ret[2]}）")
    return ret


def _main() -> int:
    if len(sys.argv) != 2:
        return 1

    out: Path
    dir: Path
    inc: regex.Pattern
    exc: regex.Pattern
    with open(sys.argv[1], "rb") as f:
        out, dir, inc, exc = pkl.load(f)
    assert dir.is_absolute() and dir.exists()

    mode: Any = {
        ".tar": "w",
        ".tgz": "w:gz",
        ".txz": "w:xz",
    }[out.suffix]
    with tarfile.open(out, mode) as tarf:

        def filter(tarinfo: tarfile.TarInfo):
            name = tarinfo.name
            if not inc.fullmatch(name) or exc.fullmatch(name):
                return None
            return tarinfo

        tarf.add(dir, arcname="/", filter=filter)

    return 0


if __name__ == "__main__":
    exit(_main())
