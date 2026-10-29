import base64
import hashlib
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class Vault:
    """Authenticated encryption for raw assets; canonical SQLite indexes remain plaintext."""

    def __init__(self, root: Path):
        self.root = root / "assets"
        self.root.mkdir(exist_ok=True)
        key_file = root / "master.key"
        if not key_file.exists():
            fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as file:
                file.write(AESGCM.generate_key(bit_length=256))
        self.key = key_file.read_bytes()
        if len(self.key) != 32:
            raise ValueError("Invalid master key")

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
