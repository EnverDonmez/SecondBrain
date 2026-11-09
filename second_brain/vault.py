import base64
import hashlib
import os
import secrets
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


DPAPI_PREFIX = b"second-brain:dpapi:v1\0"


def write_private(path: Path, content: bytes):
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def protect_key(key: bytes) -> bytes:
    if sys.platform == "win32":
        from win32crypt import CryptProtectData

        return DPAPI_PREFIX + CryptProtectData(key, "Second Brain asset key", None, None, None, 1)
    return key


class Vault:
    """Authenticated encryption for raw assets; canonical SQLite indexes remain plaintext."""

    def __init__(self, root: Path):
        self.root = root / "assets"
        self.root.mkdir(exist_ok=True)
        key_file = root / "master.key"
        if not key_file.exists():
            encoded = protect_key(AESGCM.generate_key(bit_length=256))
            fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as file:
                file.write(encoded)
        self.reload_key()

    def reload_key(self):
        path = self.root.parent / "master.key"
        encoded = path.read_bytes()
        if len(encoded) == 32:
            key = encoded
            if sys.platform == "win32":
                write_private(path, protect_key(key))
        elif sys.platform == "win32" and encoded.startswith(DPAPI_PREFIX):
            from win32crypt import CryptUnprotectData

            _, key = CryptUnprotectData(encoded[len(DPAPI_PREFIX) :], None, None, None, 1)
        else:
            raise ValueError("Invalid vault key or key belongs to a different operating system")
        if len(key) != 32:
            raise ValueError("Invalid master key")
        self.key = key

    def put(self, data: bytes, identity: str) -> str:
        nonce = secrets.token_bytes(12)
        encrypted = nonce + AESGCM(self.key).encrypt(nonce, data, identity.encode())
        target = self.path(identity)
        with target.open("xb") as f:
            f.write(encrypted)
        return hashlib.sha256(data).hexdigest()

    def path(self, identity: str) -> Path:
        if not identity or any(c not in "0123456789abcdef" for c in identity):
            raise ValueError("Invalid asset id")
        return self.root / (identity + ".enc")

    def get(self, identity: str) -> bytes:
        encrypted = self.path(identity).read_bytes()
        return AESGCM(self.key).decrypt(encrypted[:12], encrypted[12:], identity.encode())

    def erase(self, identity: str):
        self.path(identity).unlink(missing_ok=True)

    @property
    def key_fingerprint(self):
        return base64.urlsafe_b64encode(hashlib.sha256(self.key).digest()[:9]).decode()
