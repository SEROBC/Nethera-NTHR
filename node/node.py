import time
import json
import hashlib
import sqlite3
import os

BLOCK_REWARD = 50
HALVING_INTERVAL = 100

class Blockchain:

    def __init__(self):

        self.chain = []

        self.pending_transactions = []

        self.difficulty = 4

        self.block_time_target = 30

        self.max_supply = 21000000

        self.db_path = "data/blockchain.db"

        os.makedirs("data", exist_ok=True)

        self.init_db()

        self.load_chain()

        self.load_mempool()

        if len(self.chain) == 0:

            genesis = self.create_block(
                nonce=0,
                previous_hash="0"
            )

            self.chain.append(genesis)

            self.save_block(genesis)

    # -------------------------------------------------
    # DATABASE
    # -------------------------------------------------

    def init_db(self):

        conn = sqlite3.connect(self.db_path)

        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_data TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS mempool (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_data TEXT
        )
        """)

        conn.commit()
        conn.close()

    # -------------------------------------------------
    # SAVE BLOCK
    # -------------------------------------------------

    def save_block(self, block):

        conn = sqlite3.connect(self.db_path)

        c = conn.cursor()

        c.execute(
            "INSERT INTO blocks (block_data) VALUES (?)",
            (json.dumps(block),)
        )

        conn.commit()
        conn.close()

    # -------------------------------------------------
    # LOAD CHAIN
    # -------------------------------------------------

    def load_chain(self):

        conn = sqlite3.connect(self.db_path)

        c = conn.cursor()

        c.execute(
            "SELECT block_data FROM blocks ORDER BY id ASC"
        )

        rows = c.fetchall()

        conn.close()

        self.chain = []

        for row in rows:

            self.chain.append(
                json.loads(row[0])
            )

    # -------------------------------------------------
    # SAVE MEMPOOL
    # -------------------------------------------------

    def save_mempool(self):

        conn = sqlite3.connect(self.db_path)

        c = conn.cursor()

        c.execute("DELETE FROM mempool")

        for tx in self.pending_transactions:

            c.execute(
                "INSERT INTO mempool (tx_data) VALUES (?)",
                (json.dumps(tx),)
            )

        conn.commit()
        conn.close()

    # -------------------------------------------------
    # LOAD MEMPOOL
    # -------------------------------------------------

    def load_mempool(self):

        conn = sqlite3.connect(self.db_path)

        c = conn.cursor()

        c.execute(
            "SELECT tx_data FROM mempool"
        )

        rows = c.fetchall()

        conn.close()

        self.pending_transactions = []

        for row in rows:

            self.pending_transactions.append(
                json.loads(row[0])
            )

    # -------------------------------------------------
    # CREATE BLOCK
    # -------------------------------------------------

    def create_block(self, nonce, previous_hash):

        block = {
            "index": len(self.chain),
            "timestamp": time.time(),
            "transactions": self.pending_transactions,
            "nonce": nonce,
            "previous_hash": previous_hash
        }

        block["hash"] = self.hash(block)

        return block

    # -------------------------------------------------
    # HASH BLOCK
    # -------------------------------------------------

    def hash(self, block):

        block_copy = dict(block)

        if "hash" in block_copy:
            del block_copy["hash"]

        encoded = json.dumps(
            block_copy,
            sort_keys=True
        ).encode()

        return hashlib.sha256(
            encoded
        ).hexdigest()

    # -------------------------------------------------
    # GET LAST BLOCK
    # -------------------------------------------------

    def get_last_block(self):

        return self.chain[-1]

    # -------------------------------------------------
    # PROOF OF WORK
    # -------------------------------------------------

    def proof_of_work(self, previous_nonce):

        nonce = 0

        target = "0" * self.difficulty

        while True:

            guess = f"{nonce}{previous_nonce}".encode()

            guess_hash = hashlib.sha256(
                guess
            ).hexdigest()

            if guess_hash.startswith(target):

                return nonce

            nonce += 1

    # -------------------------------------------------
    # CURRENT BLOCK REWARD
    # -------------------------------------------------

    def get_block_reward(self):

        halvings = len(self.chain) // HALVING_INTERVAL

        reward = BLOCK_REWARD / (2 ** halvings)

        if reward < 0.00000001:
            reward = 0

        return reward

    # -------------------------------------------------
    # TOTAL SUPPLY
    # -------------------------------------------------

    def total_supply(self):

        total = 0

        for block in self.chain:

            for tx in block["transactions"]:

                if tx["sender"] == "network":

                    total += tx["amount"]

        return total

    # -------------------------------------------------
    # MINE BLOCK
    # -------------------------------------------------

    def mine_block(self, miner_address):

        if len(self.pending_transactions) == 0:

            return None

        # -------------------------------------
        # BLOCK REWARD + FEES
        # -------------------------------------

        reward = self.get_block_reward()

        total_fees = 0

        for tx in self.pending_transactions:

            total_fees += tx.get("fee", 0)

        reward_tx = {
            "sender": "network",
            "receiver": miner_address,
            "amount": reward + total_fees,
            "timestamp": time.time(),
            "fee": 0,
            "tx_hash": hashlib.sha256(
                f"{miner_address}{time.time()}".encode()
            ).hexdigest()
        }

        self.pending_transactions.append(
            reward_tx
        )

        # -------------------------------------
        # POW
        # -------------------------------------

        previous_block = self.get_last_block()

        previous_nonce = previous_block["nonce"]

        nonce = self.proof_of_work(
            previous_nonce
        )

        previous_hash = previous_block["hash"]

        block = self.create_block(
            nonce,
            previous_hash
        )

        # -------------------------------------
        # VALIDATE HASH
        # -------------------------------------

        block_hash = self.hash(block)

        if not block_hash.startswith(
            "0" * self.difficulty
        ):

            return None

        block["hash"] = block_hash

        # -------------------------------------
        # APPEND BLOCK
        # -------------------------------------

        self.chain.append(block)

        self.save_block(block)

        # -------------------------------------
        # CLEAR MEMPOOL
        # -------------------------------------

        self.pending_transactions = []

        self.save_mempool()

        # -------------------------------------
        # DIFFICULTY ADJUSTMENT
        # -------------------------------------

        self.adjust_difficulty()

        return block

    # -------------------------------------------------
    # DIFFICULTY RETARGET
    # -------------------------------------------------

    def adjust_difficulty(self):

        if len(self.chain) < 5:
            return

        latest = self.chain[-1]

        prev = self.chain[-5]

        actual_time = (
            latest["timestamp"]
            - prev["timestamp"]
        )

        expected_time = (
            self.block_time_target * 5
        )

        if actual_time < expected_time / 2:

            self.difficulty += 1

        elif actual_time > expected_time * 2:

            if self.difficulty > 1:
                self.difficulty -= 1

    # -------------------------------------------------
    # BALANCE
    # -------------------------------------------------

    def get_balance(self, address):

        balance = 0

        for block in self.chain:

            for tx in block["transactions"]:

                if tx["receiver"] == address:

                    balance += tx["amount"]

                if tx["sender"] == address:

                    balance -= (
                        tx["amount"]
                        + tx.get("fee", 0)
                    )

        return round(balance, 8)

    # -------------------------------------------------
    # VALIDATE CHAIN
    # -------------------------------------------------

    def is_chain_valid(self):

        for i in range(1, len(self.chain)):

            current = self.chain[i]

            previous = self.chain[i - 1]

            # HASH CHECK

            recalculated = self.hash(current)

            if current["hash"] != recalculated:

                return False

            # PREVIOUS HASH CHECK

            if current["previous_hash"] != previous["hash"]:

                return False

            # POW CHECK

            if not current["hash"].startswith(
                "0" * self.difficulty
            ):

                return False

        return True

    # -------------------------------------------------
    # REPLACE CHAIN
    # -------------------------------------------------

    def replace_chain(self, new_chain):

        if len(new_chain) <= len(self.chain):

            return False

        self.chain = new_chain

        conn = sqlite3.connect(self.db_path)

        c = conn.cursor()

        c.execute("DELETE FROM blocks")

        for block in self.chain:

            c.execute(
                "INSERT INTO blocks (block_data) VALUES (?)",
                (json.dumps(block),)
            )

        conn.commit()
        conn.close()

        return True
