import asyncio as aio
import subprocess as subp
import sys

from base import PROJECT_DIR, Path, Path_t, timetag_short
from base.progress import PROGRESS
from config import ENVIRON

from .pack import tar as pack_tar
from . import ainit_cluster, util


def dev(rm_io: bool) -> int:
    import subprocess as subp

    from . import RUNNING_DIR

    if rm_io:
        from shutil import rmtree

        from config import CONFIG

        PROGRESS(f"rm -rf {CONFIG.io_dir!r}")
        PROGRESS(f"rm -rf {CONFIG.io_dir!r}")
        PROGRESS(f"rm -rf {CONFIG.io_dir!r}")
        rmtree(CONFIG.io_dir, ignore_errors=True)

    ps = subp.Popen(
        [
            sys.executable,
            "-m",
            "entry.py",
        ],
        cwd=PROJECT_DIR,
    )
    try:
        ps.wait()
    except KeyboardInterrupt:
        try:
            ps.terminate()
            ps.wait()
        except KeyboardInterrupt:
            ps.kill()
            ps.wait()
    return ps.returncode


async def build():
    from . import RUNNING_DIR

    with PROGRESS["打包服务主体代码"]:
        path = RUNNING_DIR / "service.tgz"
        await pack_tar(
            path,
            PROJECT_DIR,
            includes=[
                r"run|run/.*",
                r"scripts|scripts/.*",
                r"base|base/.*",
                r"cluster|cluster/.*",
                r"core|core/.*",
                r"config.py",
                r"entry.py",
                r"svc_adm.py",
                r"svc_stu.py",
                r"util.py",
            ],
            excludes=[
                r"__pycache__|.*/__pycache__",
            ],
        )
        PROGRESS(f"==> {path}")

    with PROGRESS["构建 svc_adm 和 svc_stu 前端"]:

        async def build_site(cwd: Path):
            PROGRESS(f"npm install: {str(cwd)!r}")
            await util.npm_install(cwd)

            PROGRESS(f"npm build: {str(cwd)!r}")
            await util.npm_build(cwd, only=False)

            dist_dir = str(cwd / "dist")
            PROGRESS(f"tar -czf: {dist_dir!r}")
            path = RUNNING_DIR / f"{cwd.name}.tgz"
            await util.tar_cf_dir(path, dist_dir)
            PROGRESS(f"==> {path}")

        await aio.gather(
            build_site(PROJECT_DIR / "adm-site"),
            build_site(PROJECT_DIR / "stu-site"),
        )

    with PROGRESS["构建 YatCC-SE 镜像"]:
        await util.rm_rf(RUNNING_DIR / "yatcc-se")
        await util.cp_rf(RUNNING_DIR / "yatcc-se", PROJECT_DIR / "run/yatcc-se")

        tag = "yatcc-se:latest"
        await util.docker_build(
            tag, RUNNING_DIR, RUNNING_DIR / "yatcc-se/Containerfile"
        )

    PROGRESS(f"==> {tag}")


def run(
    sshd_port: int, svc_adm_port: int, svc_stu_port: int, io_dir: Path_t, *args: str
) -> int:
    return subp.run(
        [
            ENVIRON.EXECUTABLE.docker,
            *["run", "--rm", "-it"],
            *["-p", f"{sshd_port}:22"],
            *["-p", f"{svc_adm_port}:5001"],
            *["-p", f"{svc_stu_port}:5002"],
            *["-v", f"{io_dir}:/io"],
            "yatcc-se:latest",
            *args,
        ]
    ).returncode


if __name__ == "__main__":
    build()
