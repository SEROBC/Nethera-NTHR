@app.route("/tx", methods=["POST"])
def add_transaction():

    try:

        data = request.get_json()

        if not data:
            return jsonify({
                "error": "Invalid JSON"
            }), 400

        # -----------------------------------
        # REQUIRED FIELDS
        # -----------------------------------

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

        sender = str(data["sender"]).strip()
        receiver = str(data["receiver"]).strip()

        signature = data.get("signature")
        public_key = data.get("public_key")

        timestamp = data.get(
            "timestamp",
            time.time()
        )

        fee = data.get("fee", 0)

        # -----------------------------------
        # VALIDATE NUMBERS
        # -----------------------------------

        try:

            amount = float(data["amount"])
            fee = float(fee)
            timestamp = float(timestamp)

        except:

            return jsonify({
                "error": "Invalid numeric values"
            }), 400

        # -----------------------------------
        # BASIC SECURITY
        # -----------------------------------

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

        # -----------------------------------
        # TIMESTAMP VALIDATION
        # -----------------------------------

        now = time.time()

        if abs(now - timestamp) > 300:

            return jsonify({
                "error": "Transaction expired"
            }), 400

        # -----------------------------------
        # BUILD TRANSACTION
        # -----------------------------------

        tx = {
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "fee": fee,
            "timestamp": timestamp
        }

        # -----------------------------------
        # HASH TX
        # -----------------------------------

        tx_string = json.dumps(
            tx,
            sort_keys=True
        )

        tx_hash = hashlib.sha256(
            tx_string.encode()
        ).hexdigest()

        tx["tx_hash"] = tx_hash

        # -----------------------------------
        # DUPLICATE MEMPOOL CHECK
        # -----------------------------------

        for pending in app.blockchain.pending_transactions:

            if pending.get("tx_hash") == tx_hash:

                return jsonify({
                    "error": "Duplicate transaction"
                }), 400

        # -----------------------------------
        # DUPLICATE CHAIN CHECK
        # -----------------------------------

        for block in app.blockchain.chain:

            for existing_tx in block["transactions"]:

                if existing_tx.get("tx_hash") == tx_hash:

                    return jsonify({
                        "error": "Transaction already confirmed"
                    }), 400

        # -----------------------------------
        # SKIP NETWORK REWARD TX
        # -----------------------------------

        if sender != "network":

            # -----------------------------------
            # REQUIRE SIGNATURE
            # -----------------------------------

            if not signature or not public_key:

                return jsonify({
                    "error": "signature/public_key required"
                }), 400

            # -----------------------------------
            # VERIFY SIGNATURE
            # -----------------------------------

            verified = Wallet.verify_transaction(
                tx,
                signature,
                public_key
            )

            if not verified:

                return jsonify({
                    "error": "Rejected TX: Invalid signature"
                }), 400

            # -----------------------------------
            # VERIFY ADDRESS MATCH
            # -----------------------------------

            derived_address = Wallet.address_from_public_key(
                public_key
            )

            if derived_address != sender:

                return jsonify({
                    "error": "Sender address mismatch"
                }), 400

            # -----------------------------------
            # BALANCE CHECK
            # -----------------------------------

            balance = app.blockchain.get_balance(
                sender
            )

            pending_locked = 0

            for pending in app.blockchain.pending_transactions:

                if pending["sender"] == sender:

                    pending_locked += (
                        pending["amount"]
                        + pending.get("fee", 0)
                    )

            spend_total = amount + fee

            available = balance - pending_locked

            if available < spend_total:

                return jsonify({
                    "error": "Insufficient funds",
                    "balance": balance,
                    "pending_locked": pending_locked,
                    "available": available
                }), 400

        # -----------------------------------
        # ATTACH CRYPTO DATA
        # -----------------------------------

        tx["signature"] = signature
        tx["public_key"] = public_key

        # -----------------------------------
        # ADD TO MEMPOOL
        # -----------------------------------

        app.blockchain.pending_transactions.append(
            tx
        )

        # -----------------------------------
        # SAVE MEMPOOL
        # -----------------------------------

        try:

            if hasattr(app.blockchain, "save_mempool"):

                app.blockchain.save_mempool()

        except Exception as e:

            print("[MEMPOOL SAVE ERROR]", e)

        # -----------------------------------
        # P2P BROADCAST
        # -----------------------------------

        try:

            if hasattr(app, "p2p"):

                app.p2p.broadcast_transaction(tx)

        except Exception as e:

            print("[P2P ERROR]", e)

        # -----------------------------------
        # SUCCESS
        # -----------------------------------

        return jsonify({
            "message": "Transaction added",
            "tx_hash": tx_hash,
            "mempool_size": len(
                app.blockchain.pending_transactions
            ),
            "tx": tx
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500
