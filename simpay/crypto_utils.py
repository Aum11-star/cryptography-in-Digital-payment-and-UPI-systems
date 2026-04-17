"""
crypto_utils.py — Cryptographic Engine for the Secure Digital Payment Network Simulator
========================================================================================

This module implements the Hybrid Cryptography system used to secure every transaction.
The approach mirrors real-world payment network security (e.g., TLS-style hybrid encryption):

    1. RSA  (Asymmetric) — used to securely exchange the symmetric key.
    2. AES-256 (Symmetric) — used to encrypt the actual transaction payload.

Why hybrid? RSA is computationally expensive for large data. AES is fast but requires a
shared key. By combining them, we get the key-exchange security of RSA with the speed of AES.

Library used: `cryptography` (by PyCA) — a modern, well-maintained Python crypto library.
"""

import os
import base64
import hashlib
import json

from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# =============================================================================
# SECTION 1 — PASSWORD HASHING (SHA-256)
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using SHA-256.

    SHA-256 is a one-way cryptographic hash function from the SHA-2 family.
    It always produces a 256-bit (32-byte) digest, represented here as a
    64-character hexadecimal string.

    In a production system you would use bcrypt/scrypt/argon2 with a salt,
    but SHA-256 is used here to keep the demonstration straightforward.

    Args:
        password (str): The user's plaintext password.

    Returns:
        str: The 64-character hex SHA-256 digest.
    """
    # encode() converts the string to bytes (UTF-8) before hashing
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a previously stored SHA-256 hash.

    We hash the candidate password and do a simple equality check.
    Constant-time comparison (hmac.compare_digest) would be preferred in
    production to prevent timing attacks.

    Args:
        password (str): Candidate plaintext password.
        stored_hash (str): Hash stored in the database at registration time.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return hash_password(password) == stored_hash


# =============================================================================
# SECTION 2 — RSA KEY PAIR GENERATION (Asymmetric Cryptography)
# =============================================================================

def generate_rsa_key_pair():
    """
    Generate a 2048-bit RSA public/private key pair for a user.

    RSA (Rivest–Shamir–Adleman) is an asymmetric algorithm:
        • The PUBLIC key  can be shared freely and is used to ENCRYPT data.
        • The PRIVATE key must be kept secret and is used to DECRYPT data.

    Key size: 2048 bits — industry-standard minimum. 4096 bits offers more
    security but is slower; 2048 is the recommended academic demonstration size.

    Public exponent 65537 (0x10001) is a standard safe prime used in RSA.

    Returns:
        tuple: (private_key_pem, public_key_pem)
               Both as UTF-8 strings in PEM (Base64-encoded DER) format,
               which is human-readable and easy to store in a database.
    """
    # --- Step 1: Generate the private key ---
    private_key = rsa.generate_private_key(
        public_exponent=65537,   # Standard safe public exponent
        key_size=2048,           # 2048-bit key for demonstration
        backend=default_backend()
    )

    # --- Step 2: Derive the public key from the private key ---
    public_key = private_key.public_key()

    # --- Step 3: Serialize keys to PEM format (for storage/display) ---
    # PKCS8 is the standard format for storing private keys.
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()  # No passphrase for demo
    ).decode("utf-8")

    # SubjectPublicKeyInfo (SPKI) is the standard format for public keys.
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode("utf-8")

    return private_pem, public_pem


def rsa_encrypt(public_key_pem: str, plaintext: bytes) -> bytes:
    """
    Encrypt bytes using an RSA public key (OAEP padding).

    OAEP (Optimal Asymmetric Encryption Padding) with SHA-256 is the modern
    recommended RSA encryption padding. It adds randomness and prevents many
    classical attacks against textbook RSA (e.g., chosen-plaintext attacks).

    Note: RSA can only encrypt data smaller than the key size minus padding
    overhead (~190 bytes for 2048-bit OAEP-SHA256). This is why we use RSA
    only to encrypt small AES keys, NOT the entire payload.

    Args:
        public_key_pem (str): Recipient's PEM-encoded RSA public key.
        plaintext (bytes): Small data to encrypt (e.g., the AES session key).

    Returns:
        bytes: The RSA-encrypted ciphertext.
    """
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"),
        backend=default_backend()
    )

    ciphertext = public_key.encrypt(
        plaintext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return ciphertext


def rsa_decrypt(private_key_pem: str, ciphertext: bytes) -> bytes:
    """
    Decrypt RSA-encrypted bytes using a private key.

    Only the holder of the private key can decrypt data that was encrypted
    with the corresponding public key — this is the foundation of public-key
    cryptography (PKI).

    Args:
        private_key_pem (str): Holder's PEM-encoded RSA private key.
        ciphertext (bytes): The RSA-encrypted blob to decrypt.

    Returns:
        bytes: The original plaintext bytes.
    """
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend()
    )

    plaintext = private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return plaintext


# =============================================================================
# SECTION 3 — AES-256-CBC ENCRYPTION (Symmetric Cryptography)
# =============================================================================

def aes_encrypt(aes_key: bytes, plaintext: str) -> dict:
    """
    Encrypt a plaintext string using AES-256 in CBC mode.

    AES (Advanced Encryption Standard) with a 256-bit key is the gold standard
    for symmetric encryption. It is used by governments and financial institutions
    worldwide (e.g., banking, TLS/HTTPS).

    Mode: CBC (Cipher Block Chaining)
        • Each 16-byte block of plaintext is XOR'd with the previous ciphertext block
          before encryption. This means identical plaintext blocks produce different
          ciphertext blocks — defeating frequency analysis.
        • Requires a random IV (Initialization Vector) for each encryption to ensure
          that encrypting the same message twice yields different ciphertexts.

    Key size: 256 bits = 32 bytes.

    Args:
        aes_key (bytes): 32-byte (256-bit) AES key.
        plaintext (str): The transaction payload JSON string to encrypt.

    Returns:
        dict: {
            "iv_b64": str,         # Base64-encoded IV (not secret, sent with ciphertext)
            "ciphertext_b64": str  # Base64-encoded encrypted payload
        }
    """
    # --- Step 1: Generate a random 16-byte Initialization Vector (IV) ---
    # The IV must be UNIQUE for every encryption operation.
    # It does NOT need to be secret — it is transmitted alongside the ciphertext.
    iv = os.urandom(16)

    # --- Step 2: Apply PKCS7 padding to the plaintext ---
    # AES-CBC requires the plaintext to be a multiple of 16 bytes (the block size).
    # PKCS7 padding appends N bytes, each with value N, to reach the required length.
    plaintext_bytes = plaintext.encode("utf-8")
    pad_length = 16 - (len(plaintext_bytes) % 16)
    plaintext_padded = plaintext_bytes + bytes([pad_length] * pad_length)

    # --- Step 3: Create the AES cipher and encrypt ---
    cipher = Cipher(
        algorithms.AES(aes_key),   # 256-bit AES (key length determines variant)
        modes.CBC(iv),             # CBC mode with our random IV
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext_padded) + encryptor.finalize()

    # --- Step 4: Return Base64-encoded results for safe display/storage ---
    return {
        "iv_b64": base64.b64encode(iv).decode("utf-8"),
        "ciphertext_b64": base64.b64encode(ciphertext).decode("utf-8")
    }


def aes_decrypt(aes_key: bytes, iv_b64: str, ciphertext_b64: str) -> str:
    """
    Decrypt an AES-256-CBC encrypted payload back to plaintext.

    This reverses aes_encrypt(): reconstructs the cipher, decrypts, removes
    PKCS7 padding, and returns the original UTF-8 string.

    Args:
        aes_key (bytes): The 32-byte AES key (must match the one used to encrypt).
        iv_b64 (str): Base64-encoded IV from the encryption step.
        ciphertext_b64 (str): Base64-encoded ciphertext from the encryption step.

    Returns:
        str: The decrypted plaintext (original transaction payload JSON).
    """
    iv = base64.b64decode(iv_b64)
    ciphertext = base64.b64decode(ciphertext_b64)

    cipher = Cipher(
        algorithms.AES(aes_key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    # --- Remove PKCS7 padding ---
    pad_length = padded_plaintext[-1]
    plaintext_bytes = padded_plaintext[:-pad_length]

    return plaintext_bytes.decode("utf-8")


# =============================================================================
# SECTION 4 — HYBRID ENCRYPTION (Full Transaction Payload)
# =============================================================================

def encrypt_transaction_payload(receiver_public_key_pem: str, payload: dict) -> dict:
    """
    Encrypt a full transaction payload using HYBRID CRYPTOGRAPHY.

    This is the main function called when a user initiates a payment.
    It orchestrates the complete hybrid encryption pipeline:

        Payload (dict)
            │
            ▼
        [Serialize to JSON string]
            │
            ▼ AES-256-CBC (session key)
        Encrypted Payload (ciphertext_b64 + iv_b64)
            │
            ▼ RSA-OAEP (receiver's public key)
        Encrypted AES Key (encrypted_key_b64)

    The receiver (bank server) must:
        1. Decrypt the AES key using their RSA private key.
        2. Use that AES key to decrypt the actual payload.

    Args:
        receiver_public_key_pem (str): The bank/receiver's RSA public key.
        payload (dict): Transaction data, e.g.:
            {
                "sender":   "alice@simpay",
                "receiver": "bob@simpay",
                "amount":   500.0,
                "pin_hash": "<sha256 of PIN>"
            }

    Returns:
        dict: The "encrypted envelope" containing:
            - encrypted_key_b64:  RSA-encrypted AES session key
            - iv_b64:             AES initialization vector
            - ciphertext_b64:     AES-encrypted payload
    """
    # --- Step 1: Generate a fresh 256-bit AES session key ---
    # This key is used ONLY for this single transaction (ephemeral key).
    aes_key = os.urandom(32)  # 32 bytes = 256 bits

    # --- Step 2: Serialize the payload dict to a JSON string ---
    payload_json = json.dumps(payload)

    # --- Step 3: AES-encrypt the payload ---
    aes_result = aes_encrypt(aes_key, payload_json)

    # --- Step 4: RSA-encrypt the AES key using the receiver's public key ---
    # Only the holder of the matching private key can recover the AES key.
    encrypted_aes_key = rsa_encrypt(receiver_public_key_pem, aes_key)

    return {
        "encrypted_key_b64": base64.b64encode(encrypted_aes_key).decode("utf-8"),
        "iv_b64": aes_result["iv_b64"],
        "ciphertext_b64": aes_result["ciphertext_b64"]
    }


def decrypt_transaction_payload(receiver_private_key_pem: str, encrypted_envelope: dict) -> dict:
    """
    Decrypt a hybrid-encrypted transaction envelope using the receiver's RSA private key.

    This function is called by the simulated Bank Server upon receiving a transaction.
    It reverses the hybrid encryption process:

        Encrypted AES Key  ──RSA Decrypt (private key)──►  AES Key
        Ciphertext + IV    ──AES Decrypt (AES key)──────►  Payload JSON
        Payload JSON       ──JSON parse──────────────────►  dict

    Args:
        receiver_private_key_pem (str): The bank's RSA private key (kept secret).
        encrypted_envelope (dict): The output of encrypt_transaction_payload().

    Returns:
        dict: The original plaintext transaction payload.
    """
    # --- Step 1: Decode and RSA-decrypt the AES session key ---
    encrypted_aes_key = base64.b64decode(encrypted_envelope["encrypted_key_b64"])
    aes_key = rsa_decrypt(receiver_private_key_pem, encrypted_aes_key)

    # --- Step 2: AES-decrypt the payload using the recovered key ---
    payload_json = aes_decrypt(
        aes_key,
        encrypted_envelope["iv_b64"],
        encrypted_envelope["ciphertext_b64"]
    )

    # --- Step 3: Parse JSON back to a Python dict ---
    return json.loads(payload_json)


# =============================================================================
# SECTION 5 — UPI-STYLE ID GENERATOR
# =============================================================================

def generate_upi_id(username: str) -> str:
    """
    Generate a UPI-style payment ID for a user.

    Follows the pattern: <username>@simpay
    Spaces are replaced with underscores and the string is lowercased.

    Args:
        username (str): The registered username.

    Returns:
        str: e.g. "alice@simpay"
    """
    clean = username.strip().lower().replace(" ", "_")
    return f"{clean}@simpay"


# =============================================================================
# SECTION 6 — PIN HASHING
# =============================================================================

def hash_pin(pin: str) -> str:
    """
    Hash a numeric PIN using SHA-256 for secure comparison during transactions.

    The PIN is never stored in plaintext. During a transaction, the sender
    provides their PIN, which is hashed and included in the encrypted payload.
    The bank server compares this hash to the stored PIN hash.

    Args:
        pin (str): The 4–6 digit PIN as a string.

    Returns:
        str: SHA-256 hex digest of the PIN.
    """
    return hashlib.sha256(pin.encode()).hexdigest()
