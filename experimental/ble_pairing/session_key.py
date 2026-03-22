"""Tuya BLE session key derivation - REVERSE ENGINEERED from libBleLib.so.

The made_session_key() function from the native library has been disassembled
and reimplemented in Python.

The algorithm is NOT standard crypto (not AES, SHA, HKDF, etc.). It's a custom
substitution cipher using a CRC8 lookup table:

    For each byte i (0..15):
        output[i] = CRC8_TABLE[ shared_secret[i] XOR local_key[i] ]

When the shared_secret (ECDH derived) is longer than 16 bytes, there's an
additional folding step that combines bytes from the extended key.

Source: libBleLib.so from KKT.Control v2.0.9 APK
Function: made_session_key at offset 0x3060
Disassembled from ARM64 (aarch64) using objdump
"""

from __future__ import annotations


# CRC8 lookup table - loaded from crc8_table BSS symbol at 0x10fb8
# This is a standard CRC8/MAXIM table (polynomial 0x8C / reversed 0x31)
# Initialized by init_crc8() at offset 0x2c58
def _generate_crc8_table(poly: int = 0x8C) -> list[int]:
    """Generate CRC8 lookup table.

    The init_crc8() function at 0x2c58 generates this table using
    a standard CRC8 algorithm with polynomial 0x8C (reversed 0x31).

    This is CRC-8/MAXIM (aka DOW CRC, 1-Wire CRC).
    """
    table = [0] * 256
    for i in range(256):
        crc = i
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
        table[i] = crc & 0xFF
    return table


CRC8_TABLE = _generate_crc8_table(0x8C)


def made_session_key(
    shared_secret: bytes,
    key_len: int,
    local_key: bytes,
) -> bytes:
    """Derive BLE session key from ECDH shared secret and local key.

    This is a byte-for-byte reimplementation of the native made_session_key()
    function from libBleLib.so (offset 0x3060).

    Args:
        shared_secret: ECDH shared secret (x0 register, typically 32 bytes)
        key_len: Length indicator (x1 register, low byte used)
                 If <= 15: uses folding mode for longer keys
                 If > 15: uses direct 16-byte XOR + CRC8 substitution
        local_key: Local/auth key material (x2 register, 16 bytes)
                   This is BOTH input and output (modified in-place in C version)

    Returns:
        16-byte session key

    Algorithm (from disassembly):
        If key_len > 15 (0xF):
            # Direct mode - simple XOR + CRC8 substitution
            for i in 0..15:
                output[i] = CRC8_TABLE[ shared_secret[i] XOR local_key[i] ]

        If key_len <= 15:
            # Folding mode - combines overlapping bytes
            for i in 0..15:
                if i < key_len:
                    # Bytes within key_len: direct XOR + CRC8
                    xor_val = shared_secret[i] XOR local_key[i]
                else:
                    # Bytes beyond key_len: fold by adding adjacent bytes
                    fold_idx = i - key_len
                    xor_val = (shared_secret[fold_idx] + shared_secret[fold_idx + 1]) & 0xFF
                    xor_val = xor_val XOR local_key[i]

                output[i] = CRC8_TABLE[ xor_val & 0xFF ]
    """
    output = bytearray(local_key[:16])  # Copy of local_key (modified in place in C)
    key_len_byte = key_len & 0xFF

    if key_len_byte > 0xF:
        # Direct mode: each output byte = CRC8_TABLE[secret[i] XOR key[i]]
        for i in range(16):
            xor_val = shared_secret[i] ^ output[i]
            output[i] = CRC8_TABLE[xor_val & 0xFF]
    else:
        # Folding mode: handles shorter shared secrets
        for i in range(16):
            if i < key_len_byte:
                # Within key_len: direct XOR
                xor_val = shared_secret[i] ^ output[i]
            else:
                # Beyond key_len: fold by summing adjacent shared_secret bytes
                fold_idx = i - key_len_byte
                folded = (shared_secret[fold_idx] + shared_secret[fold_idx + 1]) & 0xFF
                xor_val = folded ^ output[i]

            output[i] = CRC8_TABLE[xor_val & 0xFF]

    return bytes(output)


# =============================================================================
# Verification
# =============================================================================

def _verify_crc8_table() -> None:
    """Verify our CRC8 table matches known values."""
    # CRC8/MAXIM (poly 0x8C) known test vectors
    assert CRC8_TABLE[0] == 0x00, f"CRC8[0] = {CRC8_TABLE[0]:02x}, expected 0x00"
    assert CRC8_TABLE[1] == 0x5E, f"CRC8[1] = {CRC8_TABLE[1]:02x}, expected 0x5E"
    assert CRC8_TABLE[0xFF] == 0x35, f"CRC8[0xFF] = {CRC8_TABLE[0xFF]:02x}, expected 0x35"
    print("CRC8 table verification: PASSED")


def _demo() -> None:
    """Demo the session key derivation."""
    print("=" * 60)
    print("Tuya BLE Session Key Derivation")
    print("Reverse-engineered from libBleLib.so")
    print("=" * 60)

    _verify_crc8_table()

    # Example: 32-byte ECDH shared secret + 16-byte local key
    # (In practice these come from the ECDH exchange and cloud API)
    example_secret = bytes(range(32))  # Placeholder
    example_local_key = bytes([0x42] * 16)  # Placeholder

    # key_len=32 triggers direct mode (> 0xF)
    session_key = made_session_key(example_secret, 32, example_local_key)

    print(f"\nInput shared_secret: {example_secret[:16].hex()}...")
    print(f"Input local_key:     {example_local_key.hex()}")
    print(f"Output session_key:  {session_key.hex()}")
    print(f"Session key length:  {len(session_key)} bytes")

    print("\n--- Algorithm ---")
    print("For each byte i (0..15):")
    print("  session_key[i] = CRC8_TABLE[ shared_secret[i] XOR local_key[i] ]")
    print()
    print("Where CRC8_TABLE is a standard CRC-8/MAXIM lookup table (poly 0x8C)")
    print()
    print("This is NOT standard AES/SHA/HKDF - it's a custom substitution cipher.")
    print("The CRC8 table provides non-linear mixing, while XOR combines the two inputs.")


# =============================================================================
# BLE Packet Encryption/Decryption - REVERSE ENGINEERED from bppdpdq.java
# =============================================================================
#
# The native libBleLib.so contains NO encryption - only packet framing + key derivation.
# The actual encryption is in the Java layer: com.thingclips.sdk.bluetooth.bppdpdq
#
# Algorithm: AES-128-CBC with PKCS5Padding
# Key: Session key from made_session_key() (16 bytes)
# IV: Random 16 bytes, prepended to ciphertext
#
# Encrypt format (for sending to device):
#   1. Generate random 16-byte IV
#   2. AES-128-CBC encrypt plaintext with session_key and IV
#   3. Output = IV (16 bytes) || ciphertext
#   4. Base64 encode the output
#
# Decrypt format (for received data):
#   1. Base64 decode input
#   2. First 16 bytes = IV
#   3. Remaining bytes = ciphertext
#   4. AES-128-CBC decrypt with session_key and IV
#

import os

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding as crypto_padding
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


def ble_encrypt(plaintext: bytes, session_key: bytes, iv: bytes | None = None) -> bytes:
    """Encrypt data for BLE transmission.

    Reimplementation of bppdpdq.pdqppqb() (encrypt method).

    Args:
        plaintext: Data to encrypt
        session_key: 16-byte session key from made_session_key()
        iv: 16-byte IV (random if not provided)

    Returns:
        IV (16 bytes) || AES-CBC ciphertext
    """
    if not HAS_CRYPTO:
        raise ImportError("pip install cryptography")

    if iv is None:
        iv = os.urandom(16)

    # PKCS5/PKCS7 padding
    padder = crypto_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()

    # AES-128-CBC encrypt
    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    # Output: IV || ciphertext (matching bppdpdq.java line 228-230)
    return iv + ciphertext


def ble_decrypt(data: bytes, session_key: bytes) -> bytes:
    """Decrypt data received over BLE.

    Reimplementation of bppdpdq.bdpdqbp() (decrypt method).

    Args:
        data: IV (16 bytes) || AES-CBC ciphertext
        session_key: 16-byte session key from made_session_key()

    Returns:
        Decrypted plaintext
    """
    if not HAS_CRYPTO:
        raise ImportError("pip install cryptography")

    # Extract IV (first 16 bytes) and ciphertext (rest)
    # Matching bppdpdq.java lines 53-56
    iv = data[:16]
    ciphertext = data[16:]

    # AES-128-CBC decrypt
    cipher = Cipher(algorithms.AES(session_key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()

    # Remove PKCS5/PKCS7 padding
    unpadder = crypto_padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded) + unpadder.finalize()

    return plaintext


def _test_encrypt_decrypt() -> None:
    """Test encrypt/decrypt roundtrip."""
    if not HAS_CRYPTO:
        print("SKIP: cryptography library not installed")
        return

    session_key = bytes(range(16))  # Test key
    plaintext = b"Hello Tuya BLE!"

    encrypted = ble_encrypt(plaintext, session_key)
    decrypted = ble_decrypt(encrypted, session_key)

    assert decrypted == plaintext, f"Roundtrip failed: {decrypted} != {plaintext}"
    print(f"Encrypt/Decrypt roundtrip: PASSED")
    print(f"  Plaintext:  {plaintext}")
    print(f"  Encrypted:  {encrypted.hex()} ({len(encrypted)} bytes)")
    print(f"  Decrypted:  {decrypted}")
    print(f"  IV:         {encrypted[:16].hex()}")
    print(f"  Ciphertext: {encrypted[16:].hex()}")


if __name__ == "__main__":
    _demo()
    print()
    _test_encrypt_decrypt()
