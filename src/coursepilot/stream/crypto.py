"""RFC 8216 AES-128 decryption and implicit IV derivation."""

from __future__ import annotations

import logging
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

logger = logging.getLogger(__name__)


def derive_implicit_iv(sequence_number: int) -> bytes:
    """Derive implicit IV from sequence number per RFC 8216 §5.2.
    
    The sequence number must be represented as a 16-octet big-endian integer.
    """
    return sequence_number.to_bytes(16, byteorder="big")


def decrypt_aes_128_segment(encrypted_data: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypt AES-128-CBC encrypted TS segment data per RFC 8216.
    
    Args:
        encrypted_data: Raw encrypted bytes.
        key: 16-byte AES-128 key.
        iv: 16-byte initialization vector (explicit or implicit sequence IV).
        
    Returns:
        Decrypted segment bytes. Gracefully falls back to raw decrypted bytes
        if PKCS7 unpadding fails due to block-aligned TS stream payload.
    """
    if len(key) != 16:
        raise ValueError(f"AES-128 key must be exactly 16 bytes, got {len(key)}")
    if len(iv) != 16:
        raise ValueError(f"Initialization vector (IV) must be exactly 16 bytes, got {len(iv)}")

    if not encrypted_data:
        return b""

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    decrypted_raw = decryptor.update(encrypted_data) + decryptor.finalize()

    # Attempt PKCS7 unpadding
    try:
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(decrypted_raw) + unpadder.finalize()
    except ValueError as e:
        logger.debug(
            "PKCS7 unpadding failed (%s); returning raw decrypted bytes (block-aligned MPEG-TS).",
            e,
        )
        return decrypted_raw
