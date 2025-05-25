from base64 import b64decode, b64encode
from hashlib import blake2b

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms

from . import CONFIG

_api_key_ci = Cipher(
    algorithms.ChaCha20(
        CONFIG.api_key_secret,
        CONFIG.api_key_secret[::2],
    ),
    mode=None,
)


def api_key_enc(key: str) -> str:
    """加密 API-KEY"""
    hasher = blake2b(digest_size=16)
    hasher.update(key.encode())
    enc = _api_key_ci.encryptor()
    prefix = enc.update(hasher.digest()) + enc.finalize()
    return b64encode(prefix).decode() + ":" + key


def api_key_dec(api_key: str) -> str | None:
    """解密 API-KEY"""
    try:
        colon = api_key.index(":")
        if colon == -1:
            return None
        prefix = b64decode(api_key[:colon].encode())
        dec = _api_key_ci.decryptor()
        hash = dec.update(prefix) + dec.finalize()

        key = api_key[colon + 1 :]
        hasher = blake2b(digest_size=16)
        hasher.update(key.encode())
        if hasher.digest() != hash:
            return None
        return key
    except Exception:
        return None
