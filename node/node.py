from flask import Flask, request, jsonify

import os
import time
import requests

from core.blockchain import Blockchain
from core.wallet import Wallet

app = Flask(__name__)

# =========================================================
# BLOCKCHAIN
# =========================================================

app.blockchain = Blockchain()

# =========================================================
# PEERS
# =========================================================

peers = set()

# =========================================================
# ROOT
# =========================================================

@app.route("/")
def home():

    return jsonify({
        "name": "Nethera-NTHR",
        "status": "online",
        "chain_height": len(
            app.blockchain.chain
        ),
        "difficulty": app.blockchain.difficulty,
        "pending_transactions": len(
            app.blockchain.pending_transactions
        )
    })

# =========================================================
# GET CHAIN
# =========================================================

@app.route("/chain", methods=["GET"])
def get_chain():

    return jsonify(
        app.blockchain.chain
    )

# =========================================================
# VALIDATE CHAIN
# =========================================================

@app.route("/validate", methods=["GET"])
def validate_chain():

    valid = app.blockchain.is_chain_valid()

    return jsonify({
        "valid": valid
    })

# =========================================================
# BALANCE
# =========================================================

@app.route("/balance/<address>", methods=["GET"])
def balance(address):

    amount = app.blockchain.get_balance(
        address
    )

    return jsonify({
        "address": address,
        "balance": amount
    })

# =========================================================
# TRANSACTION ROUTE
# =========================================================

@app.route("/tx", methods=["POST"])
def add_transaction():

    try:

        data = request.json

        # ======================================
        # REQUIRED FIELDS
        # ======================================

        required = [
            "sender",
            "receiver",
            "amount"
        ]

        for field in required:

            if field not in data:

                return jsonify({
                    "error": f"Missing field: {field}"
                }), 400

        sender = data["sender"]

        receiver = data["receiver"]

        amount = float(data["amount"])

        fee = float(
            data.get("fee", 0)
        )

        timestamp = data.get(
            "timestamp",
            time.time()
        )

        signature = data.get(
            "signature"
        )

        public_key = data.get(
            "public_key"
        )

        # ======================================
        # SECURITY CHECKS
        # ======================================

        if amount <= 0:

            return jsonify({
                "error": "Invalid amount"
            }), 400

        if fee < 0:

            return jsonify({
                "error": "Invalid fee"
            }), 400

        if sender == receiver:

            return jsonify({
                "error": "Cannot send to self"
            }), 400

        # ======================================
        # BUILD TX
        # ======================================

        tx = {
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "fee": fee,
            "timestamp": timestamp
        }

        # ======================================
        # VERIFY SIGNATURE
        # ======================================

        if sender != "network":

            if not signature or not public_key:

                return jsonify({
                    "error": "Signature required"
                }), 400

            verified = (
                Wallet.verify_transaction(
                    tx,
                    signature,
                    public_key
                )
            )

            if not verified:

                return jsonify({
                    "error":
                    "Rejected TX: Invalid signature"
                }), 400

            derived_address = (
                Wallet.address_from_public_key(
                    public_key
                )
            )

            if derived_address != sender:

                return jsonify({
                    "error":
                    "Sender address mismatch"
                }), 400

            # ==================================
            # BALANCE CHECK
            # ==================================

            balance = (
                app.blockchain.get_balance(
                    sender
                )
            )

            pending_locked = 0

            for pending in (
                app.blockchain.pending_transactions
            ):

                if pending["sender"] == sender:

                    pending_locked += (
                        pending["amount"]
                        + pending.get("fee", 0)
                    )

            available = (
                balance - pending_locked
            )

            if available < (
                amount + fee
            ):

                return jsonify({
                    "error":
                    "Insufficient funds",
                    "balance":
                    balance,
                    "available":
                    available
                }), 400

        # ======================================
        # ATTACH CRYPTO DATA
        # ======================================

        tx["signature"] = signature

        tx["public_key"] = public_key

        # ======================================
        # ADD TO MEMPOOL
        # ======================================

        app.blockchain.pending_transactions.append(
            tx
        )

        # ======================================
        # BROADCAST TO PEERS
        # ======================================

        for peer in peers:

            try:

                requests.post(
                    f"{peer}/receive_tx",
                    json=tx,
                    timeout=3
                )

            except:
                pass

        return jsonify({
            "message":
            "Transaction added",
            "tx": tx,
            "mempool_size":
            len(
                app.blockchain.pending_transactions
            )
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# RECEIVE TX FROM PEER
# =========================================================

@app.route("/receive_tx", methods=["POST"])
def receive_tx():

    tx = request.json

    app.blockchain.pending_transactions.append(
        tx
    )

    return jsonify({
        "message": "TX received"
    })

# =========================================================
# MINE BLOCK
# =========================================================

@app.route("/mine", methods=["GET"])
def mine():

    miner = request.args.get(
        "miner",
        "miner"
    )

    block = app.blockchain.mine_block(
        miner
    )

    if not block:

        return jsonify({
            "message":
            "No transactions to mine"
        })

    # ==========================================
    # BROADCAST BLOCK
    # ==========================================

    for peer in peers:

        try:

            requests.post(
                f"{peer}/receive_block",
                json=block,
                timeout=3
            )

        except:
            pass

    return jsonify({
        "message": "Block mined",
        "block": block
    })

# =========================================================
# RECEIVE BLOCK
# =========================================================

@app.route("/receive_block", methods=["POST"])
def receive_block():

    block = request.json

    last_block = (
        app.blockchain.get_last_block()
    )

    if (
        block["previous_hash"]
        == last_block["hash"]
    ):

        app.blockchain.chain.append(
            block
        )

        app.blockchain.db.save_block(
            block
        )

        return jsonify({
            "message":
            "Block accepted"
        })

    return jsonify({
        "error":
        "Rejected block"
    }), 400

# =========================================================
# PEER REGISTRATION
# =========================================================

@app.route("/peers", methods=["POST"])
def add_peer():

    data = request.json

    node = data.get("node")

    if not node:

        return jsonify({
            "error": "No node provided"
        }), 400

    peers.add(node)

    return jsonify({
        "message":
        "Peer added",
        "peers":
        list(peers)
    })

# =========================================================
# LIST PEERS
# =========================================================

@app.route("/peers", methods=["GET"])
def get_peers():

    return jsonify({
        "peers": list(peers)
    })

# =========================================================
# SYNC CHAIN
# =========================================================

@app.route("/sync", methods=["GET"])
def sync():

    longest_chain = (
        app.blockchain.chain
    )

    for peer in peers:

        try:

            response = requests.get(
                f"{peer}/chain",
                timeout=5
            )

            chain = response.json()

            if len(chain) > len(longest_chain):

                longest_chain = chain

        except:
            pass

    if (
        longest_chain
        != app.blockchain.chain
    ):

        app.blockchain.replace_chain(
            longest_chain
        )

        return jsonify({
            "message":
            "Chain updated",
            "length":
            len(longest_chain)
        })

    return jsonify({
        "message":
        "Already synced"
    })

# =========================================================
# SUPPLY
# =========================================================

@app.route("/supply", methods=["GET"])
def supply():

    return jsonify({

        "total_supply":
        app.blockchain.total_supply,

        "max_supply":
        app.blockchain.max_supply,

        "remaining_supply":
        round(
            app.blockchain.max_supply
            - app.blockchain.total_supply,
            8
        ),

        "current_reward":
        app.blockchain.get_block_reward(),

        "halving_interval":
        app.blockchain.halving_interval,

        "height":
        len(app.blockchain.chain)
    })

# =========================================================
# REWARD INFO
# =========================================================

@app.route("/reward", methods=["GET"])
def reward():

    height = len(
        app.blockchain.chain
    )

    next_halving = (
        (
            height
            // app.blockchain.halving_interval
        ) + 1
    ) * app.blockchain.halving_interval

    return jsonify({

        "current_reward":
        app.blockchain.get_block_reward(),

        "block_height":
        height,

        "next_halving_at":
        next_halving
    })

# =========================================================
# START NODE
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
