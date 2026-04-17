"""
database.py — SQLite Ledger & User Store for SimPay
====================================================

Manages all persistent data for the payment network simulator using SQLite,
a lightweight, file-based relational database.

Tables:
    users        — Registered users (credentials, UPI IDs, RSA keys, balance, PIN)
    transactions — Immutable ledger of all payment events

The bank server's RSA key pair is also generated and stored here on first run,
to simulate a real payment gateway that holds its own cryptographic identity.
"""

import sqlite3
import os
import json
from datetime import datetime
from crypto_utils import (
    generate_rsa_key_pair, hash_password, hash_pin, generate_upi_id
)

# Path to the SQLite database file (created in the data/ subdirectory)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "simpay.db")

# Path to store the bank server's RSA key pair (JSON file)
BANK_KEYS_PATH = os.path.join(os.path.dirname(__file__), "data", "bank_keys.json")

# Starting balance given to every new user (in INR)
INITIAL_BALANCE = 10000.0


def get_connection() -> sqlite3.Connection:
    """
    Open (or create) the SQLite database and return a connection.

    check_same_thread=False allows the connection to be used across Streamlit
    re-runs without threading errors.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Rows behave like dicts
    return conn


def initialize_database():
    """
    Create all required tables if they do not already exist.
    Called once at app startup.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --- Users table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            upi_id        TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            pin_hash      TEXT    NOT NULL,
            public_key    TEXT    NOT NULL,
            private_key   TEXT    NOT NULL,
            balance       REAL    NOT NULL DEFAULT 10000.0,
            created_at    TEXT    NOT NULL
        )
    """)

    # --- Transactions table ---
    # Each row is an immutable record of a payment event.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_upi      TEXT    NOT NULL,
            receiver_upi    TEXT    NOT NULL,
            amount          REAL    NOT NULL,
            status          TEXT    NOT NULL,   -- 'SUCCESS' or 'FAILED'
            failure_reason  TEXT,               -- NULL on success
            timestamp       TEXT    NOT NULL,
            encrypted_envelope TEXT            -- JSON-serialized encrypted blob
        )
    """)

    conn.commit()
    conn.close()


def get_or_create_bank_keys() -> dict:
    """
    Load the bank server's RSA key pair from disk, generating it if it doesn't exist.

    The bank server acts as the payment gateway — it holds a permanent RSA key pair.
    All transaction payloads are encrypted with the bank's PUBLIC key, so only
    the bank's PRIVATE key can decrypt them.

    Returns:
        dict: {"private_key": str, "public_key": str} — PEM-encoded key pair.
    """
    os.makedirs(os.path.dirname(BANK_KEYS_PATH), exist_ok=True)

    if os.path.exists(BANK_KEYS_PATH):
        with open(BANK_KEYS_PATH, "r") as f:
            return json.load(f)

    # Generate and persist bank keys on first run
    private_pem, public_pem = generate_rsa_key_pair()
    keys = {"private_key": private_pem, "public_key": public_pem}

    with open(BANK_KEYS_PATH, "w") as f:
        json.dump(keys, f)

    return keys


# =============================================================================
# USER OPERATIONS
# =============================================================================

def register_user(username: str, password: str, pin: str) -> dict:
    """
    Register a new user in the system.

    Steps:
        1. Validate username uniqueness.
        2. Hash the password and PIN with SHA-256.
        3. Generate a UPI ID (e.g., alice@simpay).
        4. Generate an RSA key pair for the user.
        5. Insert the record into the users table.

    Args:
        username (str): Desired username.
        password (str): Plaintext password (will be hashed).
        pin (str): 4–6 digit numeric PIN (will be hashed).

    Returns:
        dict: {"success": bool, "message": str, "upi_id": str or None}
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Check if username already taken
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        return {"success": False, "message": "Username already exists.", "upi_id": None}

    upi_id = generate_upi_id(username)
    password_hash = hash_password(password)
    pin_hash = hash_pin(pin)

    # Generate RSA keys for this user
    private_pem, public_pem = generate_rsa_key_pair()

    timestamp = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO users
            (username, upi_id, password_hash, pin_hash, public_key, private_key, balance, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (username, upi_id, password_hash, pin_hash, public_pem, private_pem, INITIAL_BALANCE, timestamp))

    conn.commit()
    conn.close()

    return {"success": True, "message": f"Account created! Your UPI ID: {upi_id}", "upi_id": upi_id}


def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate a user by verifying their password hash.

    Returns the full user record on success (excluding private key for safety).

    Args:
        username (str): The username to look up.
        password (str): The candidate plaintext password.

    Returns:
        dict: {"success": bool, "user": dict or None, "message": str}
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {"success": False, "user": None, "message": "User not found."}

    if not (hash_password(password) == row["password_hash"]):
        return {"success": False, "user": None, "message": "Incorrect password."}

    return {
        "success": True,
        "user": dict(row),
        "message": "Login successful."
    }


def get_user_by_upi(upi_id: str) -> dict | None:
    """
    Fetch a user record by their UPI ID.

    Args:
        upi_id (str): e.g. "bob@simpay"

    Returns:
        dict or None: Full user row as a dict, or None if not found.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE upi_id = ?", (upi_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_users() -> list:
    """
    Return a list of all registered users (safe fields only — no keys or hashes).
    Used by the admin dashboard.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, upi_id, balance, created_at FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =============================================================================
# TRANSACTION OPERATIONS
# =============================================================================

def record_transaction(
    sender_upi: str,
    receiver_upi: str,
    amount: float,
    status: str,
    failure_reason: str = None,
    encrypted_envelope: dict = None
) -> int:
    """
    Write an immutable transaction record to the ledger.

    Args:
        sender_upi (str):       Sender's UPI ID.
        receiver_upi (str):     Receiver's UPI ID.
        amount (float):         Transaction amount in INR.
        status (str):           'SUCCESS' or 'FAILED'.
        failure_reason (str):   Reason string if failed (else None).
        encrypted_envelope (dict): The full encrypted blob (for audit/display).

    Returns:
        int: The new transaction's row ID.
    """
    conn = get_connection()
    cursor = conn.cursor()

    timestamp = datetime.utcnow().isoformat()
    envelope_json = json.dumps(encrypted_envelope) if encrypted_envelope else None

    cursor.execute("""
        INSERT INTO transactions
            (sender_upi, receiver_upi, amount, status, failure_reason, timestamp, encrypted_envelope)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sender_upi, receiver_upi, amount, status, failure_reason, timestamp, envelope_json))

    txn_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return txn_id


def update_balances(sender_upi: str, receiver_upi: str, amount: float):
    """
    Atomically debit the sender and credit the receiver.

    Uses a single connection and commit to ensure both updates happen together
    (simulating a database transaction / ACID compliance).

    Args:
        sender_upi (str):   UPI ID of the sender (debit).
        receiver_upi (str): UPI ID of the receiver (credit).
        amount (float):     Amount to transfer.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET balance = balance - ? WHERE upi_id = ?", (amount, sender_upi))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE upi_id = ?", (amount, receiver_upi))

    conn.commit()
    conn.close()


def get_all_transactions() -> list:
    """
    Return all transaction records from the ledger.
    Used by the admin analytics dashboard.

    Returns:
        list[dict]: All rows from the transactions table.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sender_upi, receiver_upi, amount, status, failure_reason, timestamp
        FROM transactions
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_transactions(upi_id: str) -> list:
    """
    Return all transactions involving a specific user (as sender or receiver).

    Args:
        upi_id (str): The user's UPI ID.

    Returns:
        list[dict]: Matching transaction rows.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, sender_upi, receiver_upi, amount, status, failure_reason, timestamp
        FROM transactions
        WHERE sender_upi = ? OR receiver_upi = ?
        ORDER BY id DESC
    """, (upi_id, upi_id))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
