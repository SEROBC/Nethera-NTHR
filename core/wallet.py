import os
import json
import time
import hashlib
import binascii

from ecdsa import (
    SigningKey,
    VerifyingKey,
    SECP256k1,
    BadSignatureError
)

WALLET_DIR = "wallets"

os.makedirs(WALLET_DIR, exist_ok=True)


class Wallet:

    # -------------------------------------------------
    # INIT
    # -------------------------------------------------

    def __init__(self, private_key=None):

        if private_key:

            self.private_key = SigningKey.from_string(
                bytes.fromhex(private_key),
                curve=SECP256k1
            )

        else:

            self.private_key = SigningKey.generate(
                curve=SECP256k1
            )

        self.public_key = (
            self.private_key.get_verifying_key()
        )

    # -------------------------------------------------
    # ADDRESS
    # -------------------------------------------------

    def get_address(self):

        pubkey_bytes = (
            self.public_key.to_string()
        )

        sha = hashlib.sha256(
            pubkey_bytes
        ).digest()

        ripe = hashlib.new(
            "ripemd160",
            sha
        ).hexdigest()

        return ripe

    # -------------------------------------------------
    # EXPORT PRIVATE KEY
    # -------------------------------------------------

    def export_private_key(self):

        return self.private_key.to_string().hex()

    # -------------------------------------------------
    # EXPORT PUBLIC KEY
    # -------------------------------------------------

    def export_public_key(self):

        return self.public_key.to_string().hex()

    # -------------------------------------------------
    # SAVE WALLET
    # -------------------------------------------------

    def save_wallet(self, filename=None):

        address = self.get_address()

        if not filename:

            filename = f"{address}.json"

        path = os.path.join(
            WALLET_DIR,
            filename
        )

        wallet_data = {
            "address": address,
            "private_key": self.export_private_key(),
            "public_key": self.export_public_key(),
            "created": time.time()
        }

        with open(path, "w") as f:

            json.dump(
                wallet_data,
                f,
                indent=4
            )

        return path

    # -------------------------------------------------
    # LOAD WALLET
    # -------------------------------------------------

    @staticmethod
    def load_wallet(path):

        with open(path, "r") as f:

            data = json.load(f)

        return Wallet(
            private_key=data["private_key"]
        )

    # -------------------------------------------------
    # IMPORT PRIVATE KEY
    # -------------------------------------------------

    @staticmethod
    def import_private_key(private_key_hex):

        return Wallet(
            private_key=private_key_hex
        )

    # -------------------------------------------------
    # ADDRESS FROM PUBLIC KEY
    # -------------------------------------------------

    @staticmethod
    def address_from_public_key(public_key_hex):

        pubkey_bytes = bytes.fromhex(
            public_key_hex
        )

        sha = hashlib.sha256(
            pubkey_bytes
        ).digest()

        ripe = hashlib.new(
            "ripemd160",
            sha
        ).hexdigest()

        return ripe

    # -------------------------------------------------
    # SIGN TRANSACTION
    # -------------------------------------------------

    def sign(self, transaction):

        tx_copy = dict(transaction)

        tx_string = json.dumps(
            tx_copy,
            sort_keys=True
        )

        tx_hash = hashlib.sha256(
            tx_string.encode()
        ).digest()

        signature = self.private_key.sign(
            tx_hash
        )

        return signature.hex()

    # -------------------------------------------------
    # VERIFY TRANSACTION
    # -------------------------------------------------

    @staticmethod
    def verify_transaction(
        transaction,
        signature_hex,
        public_key_hex
    ):

        try:

            tx_copy = dict(transaction)

            tx_string = json.dumps(
                tx_copy,
                sort_keys=True
            )

            tx_hash = hashlib.sha256(
                tx_string.encode()
            ).digest()

            public_key = VerifyingKey.from_string(
                bytes.fromhex(public_key_hex),
                curve=SECP256k1
            )

            return public_key.verify(
                bytes.fromhex(signature_hex),
                tx_hash
            )

        except (
            BadSignatureError,
            Exception
        ):

            return False

    # -------------------------------------------------
    # CREATE SIGNED TRANSACTION
    # -------------------------------------------------

    def create_transaction(
        self,
        receiver,
        amount,
        fee=0
    ):

        tx = {
            "sender": self.get_address(),
            "receiver": receiver,
            "amount": float(amount),
            "fee": float(fee),
            "timestamp": time.time()
        }

        signature = self.sign(tx)

        tx["signature"] = signature

        tx["public_key"] = (
            self.export_public_key()
        )

        tx["tx_hash"] = hashlib.sha256(
            json.dumps(
                tx,
                sort_keys=True
            ).encode()
        ).hexdigest()

        return tx

    # -------------------------------------------------
    # WALLET INFO
    # -------------------------------------------------

    def info(self):

        return {
            "address": self.get_address(),
            "public_key": self.export_public_key(),
            "private_key": self.export_private_key()
        }
