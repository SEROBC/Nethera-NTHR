# network/mempool_sync.py

import threading
import time
import requests


class MempoolSync:

    def __init__(self, blockchain, peers):

        self.blockchain = blockchain
        self.peers = peers

        self.running = False
        self.sync_interval = 15

    # -----------------------------------
    # START BACKGROUND MEMPOOL SYNC
    # -----------------------------------

    def start(self):

        if self.running:
            return

        self.running = True

        thread = threading.Thread(
            target=self.sync_loop,
            daemon=True
        )

        thread.start()

        print("[MEMPOOL] Sync service started")

    # -----------------------------------
    # STOP SERVICE
    # -----------------------------------

    def stop(self):

        self.running = False

        print("[MEMPOOL] Sync service stopped")

    # -----------------------------------
    # MAIN LOOP
    # -----------------------------------

    def sync_loop(self):

        while self.running:

            try:

                self.sync_with_peers()

            except Exception as e:

                print("[MEMPOOL SYNC ERROR]", e)

            time.sleep(self.sync_interval)

    # -----------------------------------
    # SYNC WITH ALL PEERS
    # -----------------------------------

    def sync_with_peers(self):

        if not self.peers:
            return

        for peer in list(self.peers):

            try:

                url = f"{peer}/mempool"

                response = requests.get(
                    url,
                    timeout=5
                )

                if response.status_code != 200:
                    continue

                remote_mempool = response.json()

                if not isinstance(remote_mempool, list):
                    continue

                added = 0

                for tx in remote_mempool:

                    if self.add_transaction_if_missing(tx):
                        added += 1

                if added > 0:

                    print(
                        f"[MEMPOOL] Synced {added} tx(s) from {peer}"
                    )

            except Exception as e:

                print(
                    f"[MEMPOOL PEER ERROR] {peer} -> {e}"
                )

    # -----------------------------------
    # CHECK IF TX EXISTS
    # -----------------------------------

    def tx_exists(self, tx_hash):

        # Pending transactions

        for tx in self.blockchain.pending_transactions:

            if tx.get("tx_hash") == tx_hash:
                return True

        # Confirmed chain

        for block in self.blockchain.chain:

            for confirmed in block["transactions"]:

                if confirmed.get("tx_hash") == tx_hash:
                    return True

        return False

    # -----------------------------------
    # ADD TX SAFELY
    # -----------------------------------

    def add_transaction_if_missing(self, tx):

        try:

            tx_hash = tx.get("tx_hash")

            if not tx_hash:
                return False

            # Duplicate check

            if self.tx_exists(tx_hash):
                return False

            # Minimal validation

            required = [
                "sender",
                "receiver",
                "amount",
                "timestamp",
                "tx_hash"
            ]

            for field in required:

                if field not in tx:
                    return False

            # Verify signature for non-network tx

            if tx["sender"] != "network":

                from core.wallet import Wallet

                verified = Wallet.verify_transaction(
                    {
                        "sender": tx["sender"],
                        "receiver": tx["receiver"],
                        "amount": tx["amount"],
                        "fee": tx.get("fee", 0),
                        "timestamp": tx["timestamp"]
                    },
                    tx.get("signature"),
                    tx.get("public_key")
                )

                if not verified:

                    print(
                        "[MEMPOOL] Rejected invalid signature"
                    )

                    return False

            # Add tx

            self.blockchain.pending_transactions.append(tx)

            # Save mempool

            try:

                if hasattr(self.blockchain, "save_mempool"):

                    self.blockchain.save_mempool()

            except Exception as e:

                print(
                    "[MEMPOOL SAVE ERROR]",
                    e
                )

            return True

        except Exception as e:

            print("[MEMPOOL TX ERROR]", e)

            return False

    # -----------------------------------
    # BROADCAST TX TO PEERS
    # -----------------------------------

    def broadcast_transaction(self, tx):

        for peer in list(self.peers):

            try:

                requests.post(
                    f"{peer}/tx",
                    json=tx,
                    timeout=5
                )

            except Exception as e:

                print(
                    f"[BROADCAST ERROR] {peer} -> {e}"
                )

    # -----------------------------------
    # FORCE MANUAL SYNC
    # -----------------------------------

    def manual_sync(self):

        self.sync_with_peers()

        return {
            "message": "Manual mempool sync complete",
            "mempool_size": len(
                self.blockchain.pending_transactions
            ),
            "peers": len(self.peers)
        }
