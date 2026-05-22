@app.route("/tx", methods=["POST"])
def add_transaction():

    try:
        data = request.json

        # -------------------------
        # REQUIRED FIELDS
        # -------------------------

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
        amount = data["amount"]

        signature = data.get("signature")
        public_key = data.get("public_key")

        timestamp = data.get("timestamp", time.time())

        fee = data.get("fee", 0)

        # -------------------------
        # VALIDATE TYPES
        # -------------------------

        try:
            amount = float(amount)
            fee = float(fee)
        except:
            return jsonify({
                "error": "Amount/fee must be numeric"
            }), 400

        # -------------------------
        # BASIC SECURITY
        # -------------------------

        if amount <= 0:
            return jsonify({
                "error": "Amount must be positive"
            }), 400

        if fee < 0:
            return jsonify({
                "error": "Fee cannot be negative"
            }), 400

        if sender == receiver:
            return jsonify({
                "error": "Sender and receiver cannot match"
            }), 400

        # -------------------------
        # TIMESTAMP WINDOW
        # -------------------------

        current_time = time.time()

        if abs(current_time - timestamp) > 300:
            return jsonify({
                "error": "Transaction expired"
            }), 400

        # -------------------------
        # BUILD TX OBJECT
        # -------------------------

        tx = {
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "fee": fee,
            "timestamp": timestamp
        }

        # -------------------------
        # CREATE TX HASH
        # -------------------------

        tx_string = json.dumps(
            tx,
            sort_keys=True
        )

        tx_hash = hashlib.sha256(
            tx_string.encode()
        ).hexdigest()

        tx["tx_hash"] = tx_hash

        # -------------------------
        # DUPLICATE CHECK
        # -------------------------

        # Pending TX duplicate
        for pending in app.blockchain.pending_transactions:

            if pending.get("tx_hash") == tx_hash:
                return jsonify({
                    "error": "Duplicate transaction"
                }), 400

        # Chain duplicate
        for block in app.blockchain.chain:

            for existing_tx in block["transactions"]:

                if existing_tx.get("tx_hash") == tx_hash:
                    return jsonify({
                        "error": "Transaction already confirmed"
                    }), 400

        # -------------------------
        # SYSTEM TX (MINING REWARD)
        # -------------------------

        if sender != "network":

            # -------------------------
            # SIGNATURE REQUIRED
            # -------------------------

            if not signature or not public_key:
                return jsonify({
                    "error": "Signature/public_key required"
                }), 400

            # -------------------------
            # VERIFY SIGNATURE
            # -------------------------

            verified = Wallet.verify_transaction(
                tx,
                signature,
                public_key
            )

            if not verified:
                return jsonify({
                    "error": "Rejected TX: Invalid signature"
                }), 400

            # -------------------------
            # VERIFY ADDRESS MATCH
            # -------------------------

            derived_address = Wallet.address_from_public_key(
                public_key
            )

            if derived_address != sender:
                return jsonify({
                    "error": "Sender address mismatch"
                }), 400

            # -------------------------
            # BALANCE CHECK
            # -------------------------

            balance = app.blockchain.get_balance(sender)

            pending_outgoing = 0

            for pending in app.blockchain.pending_transactions:

                if pending["sender"] == sender:
                    pending_outgoing += (
                        pending["amount"]
                        + pending.get("fee", 0)
                    )

            spend_total = amount + fee

            available = balance - pending_outgoing

            if available < spend_total:
                return jsonify({
                    "error": "Insufficient funds",
                    "balance": balance,
                    "pending_locked": pending_outgoing,
                    "available": available
                }), 400

        # -------------------------
        # ATTACH SIGNATURE
        # -------------------------

        tx["signature"] = signature
        tx["public_key"] = public_key

        # -------------------------
        # ADD TO MEMPOOL
        # -------------------------

        app.blockchain.pending_transactions.append(tx)

        # -------------------------
        # BROADCAST TO PEERS
        # -------------------------

        try:
            app.p2p.broadcast_transaction(tx)
        except Exception as e:
            print("[P2P BROADCAST ERROR]", e)

        # -------------------------
        # SAVE MEMPOOL
        # -------------------------

        try:
            if hasattr(app.blockchain, "save_mempool"):
                app.blockchain.save_mempool()
        except Exception as e:
            print("[MEMPOOL SAVE ERROR]", e)

        # -------------------------
        # RESPONSE
        # -------------------------

        return jsonify({
            "message": "Transaction added",
            "tx_hash": tx_hash,
            "tx": tx,
            "mempool_size": len(
                app.blockchain.pending_transactions
            )
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500
