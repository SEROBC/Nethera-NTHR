import hashlib
import json
import time

class Block:
    def __init__(self, index, prev_hash, transactions, nonce=0):
        self.index = index
        self.prev_hash = prev_hash
        self.transactions = transactions
        self.timestamp = time.time()
        self.nonce = nonce

    def hash(self):
        return hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()
