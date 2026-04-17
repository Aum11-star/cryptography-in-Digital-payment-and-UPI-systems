"""
bank_server.py — Simulated Bank Server / Payment Gateway
=========================================================

This module simulates what a real bank's payment processing server does when
it receives an encrypted transaction request:

    1. Receive the encrypted envelope from the sender.
    2. Decrypt the AES key using the bank's RSA private key.
    3. Decrypt the payload using the AES key.
    4. Validate the PIN hash, sender balance, and receiver existence.
    5. Update balances in the ledger atomically.
    6. Return a structured success or failure response.

In a real system, steps 1–3 happen over a mutually-authenticated TLS channel.
Here we simulate the full pipeline locally to demonstrate every concept.
"""

from crypto_utils import decrypt_transaction_payload, hash_pin, encrypt_transaction_payload
from database import (
    get_or_create_bank_keys,
    get_user_by_upi,
    record_transaction,
    update_balances
)

# Minimum allowed transaction amount (in INR)
MINIMUM_AMOUNT = 1.0

# Maximum single transaction limit (anomaly threshold)
ANOMALY_THRESHOLD = 5000.0


def process_payment(encrypted_envelope: dict, sender_upi: str) -> dict:
    """
    Core bank server function: decrypt, validate, and settle a transaction.

    This function is the "server-side" half of the payment flow. It has access
    to the bank's private RSA key and uses it to recover the AES key, then
    decrypts the full payload to perform validation.

    Args:
        encrypted_envelope (dict): The encrypted payload produced by
                                   crypto_utils.encrypt_transaction_payload().
        sender_upi (str): Provided separately (not from payload) to confirm identity.

    Returns:
        dict: {
            "success":        bool,
            "transaction_id": int or None,
            "message":        str,
            "decrypted_payload": dict or None,   # Shown in UI to prove decryption
            "is_anomalous":   bool
        }
    """
    bank_keys = get_or_create_bank_keys()
    bank_private_key = bank_keys["private_key"]

    # -------------------------------------------------------------------------
    # STEP 1: Decrypt the payload using the bank's private RSA key
    # -------------------------------------------------------------------------
    try:
        payload = decrypt_transaction_payload(bank_private_key, encrypted_envelope)
    except Exception as e:
        _record_failed(sender_upi, None, 0.0, "Decryption failed — payload corrupted.", encrypted_envelope)
        return {
            "success": False,
            "transaction_id": None,
            "message": "Decryption failed. Payload may be corrupted or tampered with.",
            "decrypted_payload": None,
            "is_anomalous": False
        }

    # Extract fields from decrypted payload
    payload_sender  = payload.get("sender")
    receiver_upi    = payload.get("receiver")
    amount          = payload.get("amount", 0)
    payload_pin_hash = payload.get("pin_hash")

    # -------------------------------------------------------------------------
    # STEP 2: Validate sender identity (anti-spoofing check)
    # -------------------------------------------------------------------------
    if payload_sender != sender_upi:
        reason = "Sender UPI mismatch — possible spoofing attempt."
        _record_failed(sender_upi, receiver_upi, amount, reason, encrypted_envelope)
        return _fail_response(reason, payload)

    # -------------------------------------------------------------------------
    # STEP 3: Fetch sender and receiver records from ledger
    # -------------------------------------------------------------------------
    sender = get_user_by_upi(sender_upi)
    receiver = get_user_by_upi(receiver_upi)

    if not sender:
        reason = "Sender account not found."
        _record_failed(sender_upi, receiver_upi, amount, reason, encrypted_envelope)
        return _fail_response(reason, payload)

    if not receiver:
        reason = f"Receiver '{receiver_upi}' does not exist."
        _record_failed(sender_upi, receiver_upi, amount, reason, encrypted_envelope)
        return _fail_response(reason, payload)

    # -------------------------------------------------------------------------
    # STEP 4: Verify PIN hash
    # The PIN was hashed client-side and embedded in the payload. The bank
    # compares it to the stored PIN hash — the raw PIN never travels in any form.
    # -------------------------------------------------------------------------
    if payload_pin_hash != sender["pin_hash"]:
        reason = "PIN verification failed — incorrect PIN."
        _record_failed(sender_upi, receiver_upi, amount, reason, encrypted_envelope)
        return _fail_response(reason, payload)

    # -------------------------------------------------------------------------
    # STEP 5: Validate amount
    # -------------------------------------------------------------------------
    if amount < MINIMUM_AMOUNT:
        reason = f"Amount ₹{amount} is below the minimum of ₹{MINIMUM_AMOUNT}."
        _record_failed(sender_upi, receiver_upi, amount, reason, encrypted_envelope)
        return _fail_response(reason, payload)

    if amount > sender["balance"]:
        reason = f"Insufficient funds. Balance: ₹{sender['balance']:.2f}, Requested: ₹{amount:.2f}."
        _record_failed(sender_upi, receiver_upi, amount, reason, encrypted_envelope)
        return _fail_response(reason, payload)

    # -------------------------------------------------------------------------
    # STEP 6: Self-transfer check
    # -------------------------------------------------------------------------
    if sender_upi == receiver_upi:
        reason = "Cannot send money to yourself."
        _record_failed(sender_upi, receiver_upi, amount, reason, encrypted_envelope)
        return _fail_response(reason, payload)

    # -------------------------------------------------------------------------
    # STEP 7: Settle the transaction — update balances atomically
    # -------------------------------------------------------------------------
    update_balances(sender_upi, receiver_upi, amount)

    # -------------------------------------------------------------------------
    # STEP 8: Record success in the ledger
    # -------------------------------------------------------------------------
    is_anomalous = amount >= ANOMALY_THRESHOLD
    txn_id = record_transaction(
        sender_upi=sender_upi,
        receiver_upi=receiver_upi,
        amount=amount,
        status="SUCCESS",
        failure_reason=None,
        encrypted_envelope=encrypted_envelope
    )

    return {
        "success": True,
        "transaction_id": txn_id,
        "message": f"Payment of ₹{amount:.2f} to {receiver_upi} was successful! Transaction ID: #{txn_id}",
        "decrypted_payload": payload,
        "is_anomalous": is_anomalous
    }


def _fail_response(reason: str, payload: dict | None) -> dict:
    """Helper: build a failed transaction response dict."""
    return {
        "success": False,
        "transaction_id": None,
        "message": reason,
        "decrypted_payload": payload,
        "is_anomalous": False
    }


def _record_failed(sender_upi, receiver_upi, amount, reason, envelope):
    """Helper: silently log a failed transaction to the ledger."""
    try:
        record_transaction(
            sender_upi=sender_upi or "unknown",
            receiver_upi=receiver_upi or "unknown",
            amount=amount,
            status="FAILED",
            failure_reason=reason,
            encrypted_envelope=envelope
        )
    except Exception:
        pass  # Don't let a logging error break the response
