"""
drama_downloader.crypto.spade
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ByteDance Spade URL obfuscation decoder (used in Fanqie / Hongguo player API).
"""

import base64
import hashlib
import re
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SPADE_CONSTANTS = bytes([
    0x4D, 0xD4, 0xC2, 0xE6, 0xB8, 0x31, 0x62, 0x09, 0x0E, 0x52, 0xB3, 0xC7, 0xA6,
    0x73, 0x3B, 0xA4, 0x1C, 0xB2, 0x46, 0x2B, 0x82, 0x9A, 0xB5, 0x8A, 0x19, 0x6B,
    0x39, 0xDB, 0x57, 0x17, 0x75, 0x24, 0xF4, 0x9B, 0xAF, 0x7F, 0x08, 0xE8, 0xD6,
    0x8D, 0x26, 0xA7, 0x2E, 0x37, 0xC1, 0xA9, 0x5A, 0x2F, 0x1F, 0x05, 0xA5, 0x18,
    0x92, 0xAE, 0xF2, 0x94, 0x97, 0x32, 0xB6, 0x2A, 0x38, 0xAA, 0xDD, 0x58,
])


def _decode_base64(s: str) -> bytes:
    s = s.strip()
    rem = len(s) % 4
    if rem:
        s += "=" * (4 - rem)
    return base64.b64decode(s)


def _bits_ones(n: int) -> int:
    cnt = 0
    while n > 0:
        cnt += n & 1
        n >>= 1
    return cnt & 0xFF


def derive_content_key(spade_a: str) -> str:
    """Derives the 32-character hex AES key from spade_a payload."""
    raw = bytearray(_decode_base64(spade_a))
    if len(raw) < 3:
        raise ValueError("spade_a is too short")

    calc_len = len(raw) - (raw[0] ^ raw[1] ^ raw[2]) + 0x2F
    if calc_len <= 0 or calc_len > len(raw) * 2:
        raise ValueError(f"spade_a computed length {calc_len} is invalid")

    if 1 + calc_len > len(raw):
        calc_len = len(raw) - 1
    if calc_len < 0x21:
        raise ValueError("spade_a payload is too short")

    payload = bytearray(raw[1 : 1 + calc_len])
    b55 = 0x55
    bf6 = 0xF6

    for i in range(len(payload)):
        if i & 1:
            prev = b55
            b55 = payload[i]
        else:
            prev = bf6
            bf6 = payload[i]

        payload[i] = (-0x15 - _bits_ones(i) + (prev ^ payload[i])) & 0xFF

    key = payload[1:0x21].decode("latin1")
    if not re.match(r"^[0-9a-fA-F]{32}$", key):
        raise ValueError("invalid content key in spade_a")

    return key.lower()


def decrypt_spade_url(encrypted_url: str, key_hex: str) -> str:
    """Decrypts ByteDance spade encrypted video URL using AES-128-CBC."""
    raw = _decode_base64(encrypted_url)
    if len(raw) < 5 or raw[0] != 0xA8 or raw[2] != 0x01 or raw[3] != 0x00:
        raise ValueError("invalid encrypted URL header")

    body = raw[4:]
    body_len = (len(body) // 16) * 16
    body = body[:body_len]
    if not body:
        raise ValueError("empty encrypted URL")

    h1 = hashlib.sha512(key_hex.encode("utf-8")).digest()
    h2 = hashlib.sha512(h1 + SPADE_CONSTANTS).digest()

    aes_key = h2[:16]
    aes_iv = h2[16:32]

    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_iv))
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(body) + decryptor.finalize()

    pad_len = decrypted[-1]
    if 1 <= pad_len <= 16 and pad_len <= len(decrypted):
        decrypted = decrypted[:-pad_len]

    return decrypted.decode("utf-8", errors="ignore").rstrip("\x00")
