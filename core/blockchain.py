import time
import json
import hashlib

from core.database import BlockchainDB


class Blockchain:

    def __init__(self):

        # ==========================================
        # DATABASE
        # ==========================================

        self.db = BlockchainDB()

        # ==========================================
        # CHAIN + MEMPOOL
        # ==========================================

        self.chain = self.db.load_chain()

        self.pending_transactions = []

        # ==========================================
        # CONSENSUS
        # ==========================================

        self.difficulty = 4

        # ==========================================
        # TOKENOMICS
        # ==========================================

        self.initial_reward = 50.0

        self.halving_interval = 100

        self.max_supply = 21000000

        self.total_supply = self.calculate_total_supply()

        # ==========================================
        # GENESIS BLOCK
        # ==========================================

        if len(self.chain) == 0:

            genesis = self.create_block(
                nonce=0,
                previous_hash="0",
                transactions=[]
            )

            self.chain.append(genesis)

            self.db.save_block(genesis)

    # =========================================================
    # HASH BLOCK
    # =========================================================

    def hash_block(self, block):

        block_copy = dict(block)

        block_copy.pop("hash", None)

        encoded = json.dumps(
            block_copy,
            sort_keys=True
        ).encode()

        return hashlib.sha256(encoded).hexdigest()

    # =========================================================
    # CREATE BLOCK
    # =========================================================

    def create_block(
        self,
        nonce,
        previous_hash,
        transactions
    ):

        block = {
            "index": len(self.chain),
            "timestamp": time.time(),
            "transactions": transactions,
            "nonce": nonce,
            "previous_hash": previous_hash
        }

        block["hash"] = self.hash_block(block)

        return block

    # =========================================================
    # GET LAST BLOCK
    # =========================================================

    def get_last_block(self):

        return self.chain[-1]

    # =========================================================
    # PROOF OF WORK
    # =========================================================

    def proof_of_work(self, previous_hash):

        nonce = 0

        target = "0" * self.difficulty

        while True:

            guess = f"{previous_hash}{nonce}".encode()

            guess_hash = hashlib.sha256(
                guess
            ).hexdigest()

            if guess_hash.startswith(target):
                return nonce

            nonce += 1

    # =========================================================
    # BLOCK REWARD
    # =========================================================

    def get_block_reward(self):

        height = len(self.chain)

        halvings = (
            height // self.halving_interval
        )

        reward = (
            self.initial_reward
            / (2 ** halvings)
        )

        # Prevent endless tiny fractions

        if reward < 0.00000001:
            reward = 0

        # Enforce max supply

        remaining = (
            self.max_supply
            - self.total_supply
        )

        if remaining <= 0:
            return 0

        if reward > remaining:
            reward = remaining

        return round(reward, 8)

    # =========================================================
    # TOTAL SUPPLY
    # =========================================================

    def calculate_total_supply(self):

        supply = 0

        for block in self.chain:

            for tx in block["transactions"]:

                if tx["sender"] == "network":

                    supply += tx["amount"]

        return round(supply, 8)

    # =========================================================
    # BALANCE
    # =========================================================

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

    # =========================================================
    # MINE BLOCK
    # =========================================================

    def mine_block(self, miner_address):

        if len(self.pending_transactions) == 0:

            return None

        previous_block = self.get_last_block()

        previous_hash = previous_block["hash"]

        # ==========================================
        # PROOF OF WORK
        # ==========================================

        nonce = self.proof_of_work(
            previous_hash
        )

        # ==========================================
        # FEES
        # ==========================================

        total_fees = 0

        for tx in self.pending_transactions:

            total_fees += tx.get("fee", 0)

        total_fees = round(total_fees, 8)

        # ==========================================
        # BLOCK REWARD
        # ==========================================

        reward = self.get_block_reward()

        reward_tx = {
            "sender": "network",
            "receiver": miner_address,
            "amount": round(
                reward + total_fees,
                8
            ),
            "fee": 0,
            "timestamp": time.time()
        }

        # ==========================================
        # BUILD BLOCK TXS
        # ==========================================

        transactions = (
            self.pending_transactions.copy()
        )

        transactions.append(reward_tx)

        # ==========================================
        # CREATE BLOCK
        # ==========================================

        block = self.create_block(
            nonce,
            previous_hash,
            transactions
        )

        self.chain.append(block)

        # ==========================================
        # SAVE BLOCK
        # ==========================================

        self.db.save_block(block)

        # ==========================================
        # UPDATE SUPPLY
        # ==========================================

        self.total_supply += reward

        self.total_supply = round(
            self.total_supply,
            8
        )

        # ==========================================
        # CLEAR MEMPOOL
        # ==========================================

        self.pending_transactions = []

        return block

    # =========================================================
    # CHAIN VALIDATION
    # =========================================================

    def is_chain_valid(self):

        for i in range(1, len(self.chain)):

            current = self.chain[i]

            previous = self.chain[i - 1]

            # ======================================
            # PREVIOUS HASH CHECK
            # ======================================

            if (
                current["previous_hash"]
                != previous["hash"]
            ):
                return False

            # ======================================
            # HASH CHECK
            # ======================================

            recalculated = self.hash_block(
                current
            )

            if current["hash"] != recalculated:
                return False

        return True

    # =========================================================
    # CHAIN REPLACEMENT
    # =========================================================

    def replace_chain(self, new_chain):

        if len(new_chain) <= len(self.chain):
            return False

        self.chain = new_chain

        self.total_supply = (
            self.calculate_total_supply()
        )

        return True
