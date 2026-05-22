# core/blockchain.py

import hashlib
import json
import time

from core.database import BlockchainDB


class Blockchain:

    def __init__(self):

        self.difficulty = 4

        self.initial_reward = 50

        self.halving_interval = 100

        self.max_supply = 21000000

        self.pending_transactions = []

        self.db = BlockchainDB()

        # LOAD CHAIN

        self.chain = self.db.load_chain()

        # LOAD MEMPOOL

        self.pending_transactions = (
            self.db.load_mempool()
        )

        # GENESIS BLOCK

        if len(self.chain) == 0:

            genesis = {

                "index": 0,

                "timestamp": time.time(),

                "transactions": [],

                "nonce": 0,

                "previous_hash": "0"

            }

            genesis["hash"] = (
                self.hash_block(genesis)
            )

            self.chain.append(genesis)

            self.db.save_block(genesis)

    # -----------------------------------
    # HASH BLOCK
    # -----------------------------------

    def hash_block(self, block):

        encoded = json.dumps(
            block,
            sort_keys=True
        ).encode()

        return hashlib.sha256(
            encoded
        ).hexdigest()

    # -----------------------------------
    # GET LAST BLOCK
    # -----------------------------------

    def get_last_block(self):

        return self.chain[-1]

    # -----------------------------------
    # CURRENT SUPPLY
    # -----------------------------------

    def current_supply(self):

        supply = 0

        for block in self.chain:

            for tx in block["transactions"]:

                if tx["sender"] == "network":
                    supply += tx["amount"]

        return supply

    # -----------------------------------
    # BLOCK REWARD
    # -----------------------------------

    def get_block_reward(self):

        halvings = (
            len(self.chain)
            // self.halving_interval
        )

        reward = (
            self.initial_reward
            / (2 ** halvings)
        )

        if reward < 0.00000001:
            reward = 0

        remaining = (
            self.max_supply
            - self.current_supply()
        )

        if remaining <= 0:
            return 0

        if reward > remaining:
            reward = remaining

        return reward

    # -----------------------------------
    # PROOF OF WORK
    # -----------------------------------

    def proof_of_work(
        self,
        previous_hash,
        transactions
    ):

        nonce = 0

        while True:

            block_data = {

                "previous_hash": previous_hash,

                "transactions": transactions,

                "nonce": nonce

            }

            block_hash = hashlib.sha256(
                json.dumps(
                    block_data,
                    sort_keys=True
                ).encode()
            ).hexdigest()

            if block_hash.startswith(
                "0" * self.difficulty
            ):

                return nonce, block_hash

            nonce += 1

    # -----------------------------------
    # MINE BLOCK
    # -----------------------------------

    def mine_block(self, miner_address):

        if len(self.pending_transactions) == 0:

            return None

        reward = self.get_block_reward()

        total_fees = 0

        for tx in self.pending_transactions:

            total_fees += tx.get("fee", 0)

        reward_tx = {

            "sender": "network",

            "receiver": miner_address,

            "amount": reward + total_fees,

            "fee": 0,

            "timestamp": time.time(),

            "tx_hash": (
                f"reward_{time.time()}"
            ),

            "signature": None,

            "public_key": None
        }

        transactions = (
            self.pending_transactions.copy()
        )

        transactions.append(reward_tx)

        previous_hash = (
            self.get_last_block()["hash"]
        )

        nonce, block_hash = (
            self.proof_of_work(
                previous_hash,
                transactions
            )
        )

        block = {

            "index": len(self.chain),

            "timestamp": time.time(),

            "transactions": transactions,

            "nonce": nonce,

            "previous_hash": previous_hash,

            "hash": block_hash
        }

        # SAVE BLOCK

        self.chain.append(block)

        self.db.save_block(block)

        # CLEAR MEMPOOL

        self.pending_transactions = []

        self.db.save_mempool([])

        return block

    # -----------------------------------
    # ADD TX
    # -----------------------------------

    def add_transaction(self, tx):

        self.pending_transactions.append(tx)

        self.db.save_mempool(
            self.pending_transactions
        )

    # -----------------------------------
    # BALANCE
    # -----------------------------------

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

    # -----------------------------------
    # CHAIN VALIDATION
    # -----------------------------------

    def is_chain_valid(self):

        for i in range(1, len(self.chain)):

            current = self.chain[i]

            previous = self.chain[i - 1]

            # HASH LINK

            if (
                current["previous_hash"]
                != previous["hash"]
            ):

                return False

            # VERIFY HASH

            recalculated = self.hash_block({

                "index": current["index"],

                "timestamp": current["timestamp"],

                "transactions": current["transactions"],

                "nonce": current["nonce"],

                "previous_hash": current["previous_hash"]

            })

            if recalculated != current["hash"]:

                return False

            # DIFFICULTY CHECK

            if not current["hash"].startswith(
                "0" * self.difficulty
            ):

                return False

        return True

    # -----------------------------------
    # CHAIN REPLACEMENT
    # -----------------------------------

    def replace_chain(self, new_chain):

        if len(new_chain) <= len(self.chain):

            return False

        self.chain = new_chain

        self.db.reset_chain()

        for block in self.chain:

            self.db.save_block(block)

        return True

    # -----------------------------------
    # CHAIN INFO
    # -----------------------------------

    def get_chain_info(self):

        return {

            "height": len(self.chain),

            "difficulty": self.difficulty,

            "pending_transactions": len(
                self.pending_transactions
            ),

            "supply": self.current_supply(),

            "reward": self.get_block_reward(),

            "valid": self.is_chain_valid()
        }
