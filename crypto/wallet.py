from ecdsa import SigningKey, SECP256k1
import hashlib

class Wallet:
    def __init__(self):
        self.private_key = SigningKey.generate(curve=SECP256k1)
        self.public_key = self.private_key.get_verifying_key()

    def address(self):
        pub = self.public_key.to_string()
        return hashlib.sha256(pub).hexdigest()
