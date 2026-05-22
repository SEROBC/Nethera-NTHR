# core/wallet.py

import os
import json
import time
import hashlib
import secrets

from ecdsa import (
    SigningKey,
    VerifyingKey,
    SECP256k1,
    BadSignatureError
)

# -----------------------------------
# EXTENDED WORDLIST
# -----------------------------------

WORDLIST = [
    "apple", "anchor", "atom", "alpha", "alert",
    "banana", "battle", "binary", "blade", "boost",
    "carbon", "chain", "cipher", "cloud", "crystal",
    "delta", "dragon", "drift", "dynamic", "dream",
    "echo", "energy", "ember", "eternal", "engine",
    "falcon", "fiber", "flame", "future", "fusion",
    "galaxy", "genesis", "ghost", "gravity", "grid",
    "hammer", "horizon", "hydra", "hyper", "helium",
    "ice", "iron", "impact", "infinite", "island",
    "jungle", "jupiter", "justice", "jet", "kernel",
    "laser", "legend", "logic", "lunar", "matrix",
    "meteor", "mining", "mirror", "nebula", "network",
    "node", "nova", "nucleus", "oasis", "omega",
    "oracle", "orbit", "phoenix", "plasma", "pulse",
    "quantum", "radar", "rocket", "shadow", "signal",
    "solar", "spirit", "storm", "summit", "system",
    "tensor", "thunder", "token", "unity", "vector",
    "velocity", "vertex", "vision", "void", "wave",
    "xenon", "yield", "zenith", "zero"
]


class Wallet:

    # -----------------------------------
    # INIT
    # -----------------------------------

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

    # -----------------------------------
    # ADDRESS
    # -----------------------------------

    def get_address(self):

        pub_hex = (
            self.public_key.to_string().hex()
        )

        return hashlib.sha256(
            pub_hex.encode()
        ).hexdigest()

    # -----------------------------------
    # PRIVATE KEY
    # -----------------------------------

    def get_private_key(self):

        return (
            self.private_key.to_string().hex()
        )

    # -----------------------------------
    # PUBLIC KEY
    # -----------------------------------

    def get_public_key(self):

        return (
            self.public_key.to_string().hex()
        )

    # -----------------------------------
    # SIGN TRANSACTION
    # -----------------------------------

    def sign(self, tx):

        tx_copy = tx.copy()

        tx_string = json.dumps(
            tx_copy,
            sort_keys=True
        )

        signature = self.private_key.sign(
            tx_string.encode()
        )

        return signature.hex()

    # -----------------------------------
    # VERIFY TX
    # -----------------------------------

    @staticmethod
    def verify_transaction(
        tx,
        signature,
        public_key
    ):

        try:

            vk = VerifyingKey.from_string(
                bytes.fromhex(public_key),
                curve=SECP256k1
            )

            tx_copy = tx.copy()

            tx_string = json.dumps(
                tx_copy,
                sort_keys=True
            )

            return vk.verify(
                bytes.fromhex(signature),
                tx_string.encode()
            )

        except BadSignatureError:

            return False

        except Exception:

            return False

    # -----------------------------------
    # PUBLIC KEY -> ADDRESS
    # -----------------------------------

    @staticmethod
    def address_from_public_key(
        public_key
    ):

        return hashlib.sha256(
            public_key.encode()
        ).hexdigest()

    # -----------------------------------
    # GENERATE SEED PHRASE
    # -----------------------------------

    @staticmethod
    def generate_seed_phrase(
        words=12
    ):

        phrase = []

        for _ in range(words):

            phrase.append(
                secrets.choice(
                    WORDLIST
                )
            )

        return " ".join(phrase)

    # -----------------------------------
    # SEED -> PRIVATE KEY
    # -----------------------------------

    @staticmethod
    def seed_to_private_key(
        seed_phrase
    ):

        hashed = hashlib.sha256(
            seed_phrase.encode()
        ).hexdigest()

        return hashed[:64]

    # -----------------------------------
    # CREATE FROM SEED
    # -----------------------------------

    @classmethod
    def from_seed_phrase(
        cls,
        seed_phrase
    ):

        private_key = (
            cls.seed_to_private_key(
                seed_phrase
            )
        )

        return cls(private_key)

    # -----------------------------------
    # CREATE NEW SEEDED WALLET
    # -----------------------------------

    @classmethod
    def create_with_seed(cls):

        seed_phrase = (
            cls.generate_seed_phrase()
        )

        wallet = cls.from_seed_phrase(
            seed_phrase
        )

        return {

            "seed_phrase": seed_phrase,

            "wallet": wallet
        }

    # -----------------------------------
    # EXPORT WALLET
    # -----------------------------------

    def export_wallet(
        self,
        filename=None,
        include_private=True
    ):

        os.makedirs(
            "wallets",
            exist_ok=True
        )

        if filename is None:

            filename = (
                f"wallet_"
                f"{int(time.time())}.json"
            )

        data = {

            "address": (
                self.get_address()
            ),

            "public_key": (
                self.get_public_key()
            )
        }

        if include_private:

            data["private_key"] = (
                self.get_private_key()
            )

        path = f"wallets/{filename}"

        with open(path, "w") as f:

            json.dump(
                data,
                f,
                indent=4
            )

        return path

    # -----------------------------------
    # EXPORT FULL BACKUP
    # -----------------------------------

    def export_backup(
        self,
        seed_phrase,
        filename=None
    ):

        os.makedirs(
            "wallets",
            exist_ok=True
        )

        if filename is None:

            filename = (
                f"backup_"
                f"{int(time.time())}.json"
            )

        backup = {

            "seed_phrase": seed_phrase,

            "private_key": (
                self.get_private_key()
            ),

            "public_key": (
                self.get_public_key()
            ),

            "address": (
                self.get_address()
            )
        }

        path = f"wallets/{filename}"

        with open(path, "w") as f:

            json.dump(
                backup,
                f,
                indent=4
            )

        return path

    # -----------------------------------
    # IMPORT WALLET FILE
    # -----------------------------------

    @classmethod
    def import_wallet(
        cls,
        filepath
    ):

        with open(filepath, "r") as f:

            data = json.load(f)

        private_key = data.get(
            "private_key"
        )

        if not private_key:

            raise Exception(
                "Private key missing"
            )

        return cls(private_key)

    # -----------------------------------
    # EXPORT TX PAYLOAD
    # -----------------------------------

    def create_signed_transaction(
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

        payload = {

            **tx,

            "signature": signature,

            "public_key": (
                self.get_public_key()
            )
        }

        return payload

    # -----------------------------------
    # WALLET INFO
    # -----------------------------------

    def info(self):

        return {

            "address": (
                self.get_address()
            ),

            "public_key": (
                self.get_public_key()
            ),

            "private_key": (
                self.get_private_key()
            )
        }
