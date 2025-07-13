from base.logger import logger
from config import CONFIG
from . import OversizeError

LOGGER = logger(__spec__, __file__)


class API_KEY:

    @classmethod
    async def get(cls) -> str:
        from . import DB0

        ret = await DB0.get("admin-api-key")
        if ret is None:
            LOGGER.debug("管理员 API-KEY 未设置，使用默认值")
            return CONFIG.CORE.default_admin_api_key
        assert type(ret) is bytes
        return ret.decode()

    @classmethod
    async def set(cls, api_key: str) -> None:
        from . import DB0

        enc = api_key.encode()
        if len(enc) > 32:
            raise OversizeError(api_key, 32, "管理员 API-KEY 过长")
        ok = await DB0.set("admin-api-key", enc)
        assert ok is True
