"""
drama_downloader.crypto.dramabox_rsa
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
RSA-SHA256 signature utility for DramaBox API requests.
"""

import base64
import re
from typing import Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

_DB_PEM_BODY = (
    "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC9Q4Y5QX5j08HrnbY3irfKdkEllAU2OORnAjlXDyCzcm2Z6ZRrGvtTZUAM"
    "elfU5PWS6XGEm3d4kJEKbXi4Crl8o2E/E3YJPk1lQD1d0JTdrvZleETN1ViHZFSQwS3L94Woh0E3TPebaEYq88eExvKu1tDdjSoFjBbgMezy"
    "Snas5Nc2xF28XhPuC8m15u+dectsrJl+ALGcTDX3Lv3FURuwV/dN7WMEkgcseIKVMdJxzUB0PeSqCNftfxmdBV/U4yXFRxPhnSFSXCrkj6uJ"
    "jickiYq1pQ1aZfrQe1eLD3MB2hKq7crhMcA3kpggQlnmy1wRR4BAttmSU4fPb/yF8D3hAgMBAAECggEBAJdru6p5RLZ3h/GLF2rud8bqv4pi"
    "F51e/RWQyPFnMAGBrkByiYT7bFI3cnvJMhYpLHRigqjWfUofV3thRDDym54lVLtTRZ91khRMxgwVwdRuk8Fw7JNFenOwCJxbgdlq6iuAMuQc"
    "lwll7qWUrm8DgMvzH93xf8o6X171cp4Sh0og1Ra7E9GZ37dzBlX2aJBK8VBfctZntuDPx52e71nafqfbjXxZuEtpu92oJd6A9mWbd0BZTk72"
    "ZHUmDcKcqjfcEH19SWOphMJFYkxU5FRoIEr3/zisyTO4Mt33ZmwELOrY9PdlyAAyed7ZoH+hlTr7c025QROvb2LmqgRiUT56tMECgYEA+jH5"
    "m6iMRK6XjiBhSUnlr3DzRybwlQrtIj5sZprWe2my5uYHG3jbViYIO7GtQvMTnDrBCxNhuM6dPrL0cRnbsp/iBMXe3pyjT/aWveBkn4R+UpBs"
    "nbtDn28r1MZpCDtr5UNc0TPj4KFJvjnV/e8oGoyYEroECqcw1LqNOGDiLhkCgYEAwaemNePYrXW+MVX/hatfLQ96tpxwf7yuHdENZ2q5AFw7"
    "3GJWYvC8VY+TcoKPAmeoCUMltI3TrS6K5Q/GoLd5K2BsoJrSxQNQFd3ehWAtdOuPDvQ5rn/2fsvgvc3rOvJh7uNnwEZCI/45WQg+UFWref4P"
    "Pc+ArNtp9Xj2y7LndwkCgYARojIQeXmhYZjG6JtSugWZLuHGkwUDzChYcIPdW25ndluokG/RzNvQn4+W/XfTryQjr7RpXm1VxCIrCBvYWNU2"
    "KrSYV4XUtL+B5ERNj6In6AOrOAifuVITy5cQQQeoD+AT4YKKMBkQfO2gnZzqb8+ox130e+3K/mufoqJPZeyrCQKBgC2fobjwhQvYwYY+DIUh"
    "arri+rYrBRYTDtJYnh/PNOaw1CmHwXJt5PEDcml3+NlIMn58I1X2U/hpDrAIl3MlxpZBkVYFI8LmlOeR7ereTddN59ZOE4jY/OnCfqA480Jf"
    "+FKfoMHby5lPO5OOLaAfjtae1FhrmpUe3EfIx9wVuhKBAoGBAPFzHKQZbGhkqmyPW2ctTEIWLdUHyO37fm8dj1WjN4wjRAI4ohNiKQJRh3QE"
    "11E1PzBTl9lZVWT8QtEsSjnrA/tpGr378fcUT7WGBgTmBRaAnv1P1n/Tp0TSvh5XpIhhMuxcitIgrhYMIG3GbP9JNAarxO/qPW6Gi0xWaF7i"
    "l7Or"
)

_private_key = None


def _read_asn1_int(buf: bytes, offset: int):
    assert buf[offset] == 0x02
    offset += 1
    if buf[offset] & 0x80:
        nbytes = buf[offset] & 0x7F
        offset += 1
        length = int.from_bytes(buf[offset : offset + nbytes], "big")
        offset += nbytes
    else:
        length = buf[offset]
        offset += 1
    val = int.from_bytes(buf[offset : offset + length], "big")
    return val, offset + length


def _build_private_key():
    der = base64.b64decode(_DB_PEM_BODY)
    octet_len = int.from_bytes(der[24:26], "big")
    rsa_der = der[26 : 26 + octet_len]

    offset = 4
    ver, offset = _read_asn1_int(rsa_der, offset)
    n, offset = _read_asn1_int(rsa_der, offset)
    e, offset = _read_asn1_int(rsa_der, offset)
    d, offset = _read_asn1_int(rsa_der, offset)
    p, offset = _read_asn1_int(rsa_der, offset)
    q, offset = _read_asn1_int(rsa_der, offset)
    dmp1_raw, offset = _read_asn1_int(rsa_der, offset)
    dmq1_raw, offset = _read_asn1_int(rsa_der, offset)
    iqmp, offset = _read_asn1_int(rsa_der, offset)

    dmp1 = d % (p - 1)
    dmq1 = d % (q - 1)

    pn = rsa.RSAPrivateNumbers(
        p=p,
        q=q,
        d=d,
        dmp1=dmp1,
        dmq1=dmq1,
        iqmp=iqmp,
        public_numbers=rsa.RSAPublicNumbers(e=e, n=n),
    )
    return pn.private_key()


def get_private_key():
    global _private_key
    if _private_key is None:
        _private_key = _build_private_key()
    return _private_key


def sign_dramabox(payload: str) -> str:
    """Signs payload with DramaBox RSA Private Key using SHA256 PKCS1v15 padding."""
    try:
        key = get_private_key()
        signature = key.sign(
            payload.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")
    except Exception:
        return ""
