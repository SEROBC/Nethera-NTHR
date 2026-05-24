# =========================================================
# Nethera-NTHR
# exchange/api.py
# REST Exchange API Layer
# =========================================================

from flask import Flask, request, jsonify

app = Flask(__name__)

ORDERS = []

BALANCES = {}

# ---------------------------------------------------------
# PLACE ORDER
# ---------------------------------------------------------

@app.route("/order", methods=["POST"])
def order():

    data = request.json

    ORDERS.append({

        "id": len(ORDERS),
        "type": data["type"],  # buy/sell
        "price": data["price"],
        "amount": data["amount"],
        "status": "open"
    })

    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# GET ORDERS
# ---------------------------------------------------------

@app.route("/orders")
def get_orders():

    return jsonify(ORDERS)

# ---------------------------------------------------------
# MATCH ENGINE (simple CEX-style)
# ---------------------------------------------------------

@app.route("/match")
def match():

    buys = [o for o in ORDERS if o["type"] == "buy"]
    sells = [o for o in ORDERS if o["type"] == "sell"]

    trades = []

    for b in buys:

        for s in sells:

            if b["price"] >= s["price"]:

                trade = {

                    "buy_id": b["id"],
                    "sell_id": s["id"],
                    "price": s["price"],
                    "amount": min(b["amount"], s["amount"])
                }

                trades.append(trade)

    return jsonify(trades)

# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(port=9000, host="0.0.0.0")
