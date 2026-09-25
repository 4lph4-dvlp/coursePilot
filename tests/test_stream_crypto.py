"""Unit tests for RFC 8216 AES-128 decryption and implicit IV derivation."""

import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from kau_assistant.stream.crypto import (
    decrypt_aes_128_segment,
    derive_implicit_iv,
)


def test_derive_implicit_iv():
    """Verify implicit IV is a 16-octet big-endian integer representation."""
    assert derive_implicit_iv(1) == b"\x00" * 15 + b"\x01"
    assert derive_implicit_iv(256) == b"\x00" * 14 + b"\x01\x00"
    assert derive_implicit_iv(0) == b"\x00" * 16
    assert len(derive_implicit_iv(12345)) == 16


def test_aes_128_roundtrip_explicit_iv():
    """Verify roundtrip encryption and decryption with explicit IV and PKCS7 padding."""
    key = b"0123456789abcdef"  # 16 bytes
    iv = b"fedcba9876543210"   # 16 bytes
    plaintext = b"Hello, this is a test segment for KAU LXP pure-python HLS streaming!"

    # Encrypt with PKCS7
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Decrypt using our function
    decrypted = decrypt_aes_128_segment(ciphertext, key, iv)
    assert decrypted == plaintext


def test_aes_128_sequence_number_iv():
    """Verify decryption when IV is derived implicitly from sequence number."""
    key = b"abcdef0123456789"
    seq = 42
    iv = derive_implicit_iv(seq)
    plaintext = b"Testing implicit IV calculation per RFC 8216 section 5.2"

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    ciphertext = cipher.encryptor().update(padded_data) + cipher.encryptor().finalize()

    decrypted = decrypt_aes_128_segment(ciphertext, key, iv)
    assert decrypted == plaintext


def test_aes_128_pkcs7_padding_fallback():
    """Verify fallback to raw decrypted bytes when data is block-aligned without PKCS7 padding."""
    key = b"1111222233334444"
    iv = b"5555666677778888"
    # Exact multiple of 16 bytes, but arbitrary raw bytes that do not form valid PKCS7 padding
    # e.g., ending with 0x00
    raw_payload = b"A" * 15 + b"\x00"  # 16 bytes, invalid PKCS7 (last byte cannot be 0)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    ciphertext = cipher.encryptor().update(raw_payload) + cipher.encryptor().finalize()

    decrypted = decrypt_aes_128_segment(ciphertext, key, iv)
    assert decrypted == raw_payload


def test_aes_128_invalid_key_or_iv_length():
    """Verify ValueError is raised if key or IV is not 16 bytes."""
    valid_key = b"0123456789abcdef"
    valid_iv = b"0123456789abcdef"
    short_key = b"12345"
    short_iv = b"12345"

    with pytest.raises(ValueError, match="AES-128 key must be exactly 16 bytes"):
        decrypt_aes_128_segment(b"data", short_key, valid_iv)

    with pytest.raises(ValueError, match="Initialization vector .* must be exactly 16 bytes"):
        decrypt_aes_128_segment(b"data", valid_key, short_iv)
