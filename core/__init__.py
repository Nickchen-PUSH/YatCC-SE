"""核心层，包含系统状态访问的全部操作原语

所有的操作原语设计都必须遵循以下几点：
  1. 定义为 async def 异步函数，或返回协程且前置代码不操作系统状态；
  2. 原语只应返回成功一种情况的结果，其它所有错误通过异常抛出；
  3. 原语必须保证异常安全性，在无法保证一致性的情况下，设置资源为死状态；
  4. 使用类和类方法分组原语，类名使用全大写加下划线；
"""

import asyncio as aio
import os

import redis.asyncio
import redis.asyncio.client

from base import guard_ainit
from base.logger import logger

import cluster

LOGGER = logger(__spec__, __file__)


# 数据库连接
DB0: redis.asyncio.Redis
DB_STU: redis.asyncio.Redis


@guard_ainit(LOGGER)
async def ainit(
    *,
    cluster_mock=False,
) -> None:
    global DB0, DB_STU, CLUSTER

    from config import CONFIG

    DB0 = redis.asyncio.Redis(**CONFIG.CORE.redis_init, db=0)
    DB_STU = redis.asyncio.Redis(**CONFIG.CORE.redis_init, db=1)

    os.makedirs(CONFIG.CORE.students_dir, mode=0o777, exist_ok=True)
    os.makedirs(CONFIG.CORE.archive_students_dir, mode=0o777, exist_ok=True)

    CLUSTER = cluster.create(mock=cluster_mock)


async def ready() -> bool:
    global DB0, DB_STU
    try:
        return all(await aio.gather(DB0.ping(), DB_STU.ping()))
    except redis.RedisError:
        return False

# ==================================================================================== #

class Error(Exception):
    pass
