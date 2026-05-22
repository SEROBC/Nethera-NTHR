from flask import Flask, request, jsonify

import uuid
import time
import requests

app = Flask(__name__)

# =========================================================
# CONFIG
# =========================================================

BLOCKCHAIN_NODE = "http://127.0.0.1:5000"

USD_RATE = 1.00

# =========================================================
# IN-MEMORY INVOICES
# =========================================================

invoices = {}

# =========================================================
# HEALTH
# =========================================================

@app.route("/")
def home():

    return jsonify({
        "service": "Nethera Gateway",
        "status": "online",
        "asset": "NTHR",
        "usd_rate": USD_RATE
    })

# =========================================================
# CREATE PAYMENT INVOICE
# =========================================================

@app.route("/create_invoice", methods=["POST"])
def create_invoice():

    try:

        data = request.json

        merchant = data.get("merchant")

        usd_amount = float(
            data.get("usd_amount")
        )

        payout_address = data.get(
            "payout_address"
        )

        if not merchant:

            return jsonify({
                "error": "merchant required"
            }), 400

        if usd_amount <= 0:

            return jsonify({
                "error": "invalid usd_amount"
            }), 400

        if not payout_address:

            return jsonify({
                "error":
                "payout_address required"
            }), 400

        # ======================================
        # CONVERT USD -> NTHR
        # ======================================

        nthr_amount = round(
            usd_amount / USD_RATE,
            8
        )

        invoice_id = str(uuid.uuid4())

        invoice = {

            "invoice_id": invoice_id,

            "merchant": merchant,

            "usd_amount": usd_amount,

            "nthr_amount": nthr_amount,

            "payout_address": payout_address,

            "status": "pending",

            "created_at": time.time(),

            "confirmations": 0,

            "tx_hash": None
        }

        invoices[invoice_id] = invoice

        return jsonify({

            "message":
            "Invoice created",

            "invoice": invoice
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# LIST INVOICES
# =========================================================

@app.route("/invoices", methods=["GET"])
def get_invoices():

    return jsonify(
        list(invoices.values())
    )

# =========================================================
# GET SINGLE INVOICE
# =========================================================

@app.route("/invoice/<invoice_id>", methods=["GET"])
def get_invoice(invoice_id):

    invoice = invoices.get(invoice_id)

    if not invoice:

        return jsonify({
            "error": "invoice not found"
        }), 404

    return jsonify(invoice)

# =========================================================
# SIMULATE PAYMENT DETECTION
# =========================================================

@app.route("/pay_invoice", methods=["POST"])
def pay_invoice():

    try:

        data = request.json

        invoice_id = data.get(
            "invoice_id"
        )

        sender = data.get("sender")

        signature = data.get(
            "signature"
        )

        public_key = data.get(
            "public_key"
        )

        invoice = invoices.get(invoice_id)

        if not invoice:

            return jsonify({
                "error": "invoice not found"
            }), 404

        if invoice["status"] == "paid":

            return jsonify({
                "error":
                "invoice already paid"
            }), 400

        # ======================================
        # BUILD BLOCKCHAIN TX
        # ======================================

        tx = {

            "sender": sender,

            "receiver":
            invoice["payout_address"],

            "amount":
            invoice["nthr_amount"],

            "fee": 0.01,

            "timestamp": time.time(),

            "signature": signature,

            "public_key": public_key
        }

        # ======================================
        # SEND TX TO BLOCKCHAIN
        # ======================================

        response = requests.post(
            f"{BLOCKCHAIN_NODE}/tx",
            json=tx,
            timeout=10
        )

        result = response.json()

        if response.status_code != 200:

            return jsonify({
                "error":
                "blockchain rejected tx",
                "details": result
            }), 400

        invoice["status"] = "paid"

        invoice["tx_hash"] = (
            result["tx"]
            .get("tx_hash")
        )

        invoice["paid_at"] = time.time()

        return jsonify({

            "message":
            "invoice paid",

            "invoice": invoice,

            "blockchain_response":
            result
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

# =========================================================
# SIMULATE CONFIRMATION ENGINE
# =========================================================

@app.route("/confirm/<invoice_id>", methods=["POST"])
def confirm_invoice(invoice_id):

    invoice = invoices.get(invoice_id)

    if not invoice:

        return jsonify({
            "error":
            "invoice not found"
        }), 404

    if invoice["status"] != "paid":

        return jsonify({
            "error":
            "invoice not paid yet"
        }), 400

    invoice["confirmations"] += 1

    if invoice["confirmations"] >= 3:

        invoice["status"] = "confirmed"

    return jsonify({
        "invoice": invoice
    })

# =========================================================
# MERCHANT SETTLEMENT
# =========================================================

@app.route("/settle/<invoice_id>", methods=["POST"])
def settle_invoice(invoice_id):

    invoice = invoices.get(invoice_id)

    if not invoice:

        return jsonify({
            "error":
            "invoice not found"
        }), 404

    if invoice["status"] != "confirmed":

        return jsonify({
            "error":
            "invoice not confirmed"
        }), 400

    invoice["status"] = "settled"

    invoice["settled_at"] = time.time()

    return jsonify({

        "message":
        "merchant settled",

        "invoice": invoice
    })

# =========================================================
# FAKE EXCHANGE RATE
# =========================================================

@app.route("/rate", methods=["GET"])
def get_rate():

    return jsonify({

        "symbol": "NTHR/USD",

        "price": USD_RATE
    })

# =========================================================
# UPDATE EXCHANGE RATE
# =========================================================

@app.route("/rate", methods=["POST"])
def set_rate():

    global USD_RATE

    data = request.json

    USD_RATE = float(
        data.get("price")
    )

    return jsonify({

        "message":
        "rate updated",

        "new_rate":
        USD_RATE
    })

# =========================================================
# START BRIDGE
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=7000
    )
