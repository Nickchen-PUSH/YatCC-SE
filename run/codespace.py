import asyncio as aio
import subprocess as subp

from base import PROJECT_DIR, Path_t, timetag_short
from base.progress import PROGRESS
from config import ENVIRON
from run import util
from .pack import tar as pack_tar


async def build():
    from . import RUNNING_DIR

    with PROGRESS["打包程序代码"]:
        path = RUNNING_DIR / "service.tgz"
        await pack_tar(
            path,
            PROJECT_DIR,
            includes=[
                r"base|base/.*",
                r"codespace|codespace/.*",
            ],
            excludes=[
                r"__pycache__|.*/__pycache__",
            ],
        )
        PROGRESS(f"==> {path}")

    with PROGRESS["下载 code-server.deb"]:
        path = RUNNING_DIR / "code-server.deb"
        if not path.exists():
            await util.wget(
                # "https://github.com/coder/code-server/releases/download/v4.96.4/code-server_4.96.4_amd64.deb",
                "https://github.com/coder/code-server/releases/download/v4.96.4/code-server_4.96.4_arm64.deb",
                path,
            )
        PROGRESS(f"==> {path}")

    with PROGRESS["下载 cpptools-linux-x64.vsix"]:
        path = RUNNING_DIR / "cpptools-linux-x64.vsix"
        if not path.exists():
            await util.wget(
                "https://github.com/microsoft/vscode-cpptools/releases/download/v1.23.6/cpptools-linux-x64.vsix",
                path,
            )

    with PROGRESS["构建 CODESERVER 镜像"]:
        await util.rm_rf(RUNNING_DIR / "codespace")
        await util.cp_rf(RUNNING_DIR / "codespace", PROJECT_DIR / "run/codespace")

        tag = "codeserver.latest"
        await util.docker_build(
            tag, RUNNING_DIR, RUNNING_DIR / "codespace/Containerfile"
        )

    PROGRESS(f"==> {tag}")


def run(
    sshd_port: int,
    code_server_port: int,
    io_dir: Path_t,
    root_dir: Path_t,
    code_dir: Path_t,
    *args: str,
) -> int:
    return subp.run(
        [
            ENVIRON.EXECUTABLE.docker,
            *["run", "--rm", "-it"],
            *["-p", f"{sshd_port}:22"],
            *["-p", f"{code_server_port}:443"],
            *["-p", f"5900:5900"],
            *["-v", f"{io_dir}:/io"],
            *["-v", f"{root_dir}:/root"],
            *["-v", f"{code_dir}:/code"],
            "codeserver.latest",
            *args,
        ]
    ).returncode
