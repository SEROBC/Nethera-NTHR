from flask import Flask, request, jsonify
from core.blockchain import Blockchain

app = Flask(__name__)
bc = Blockchain()

@app.route("/mine")
def mine():
    bc.mine_block()
    return jsonify({"length": len(bc.chain)})

@app.route("/chain")
def chain():
    return jsonify([b.__dict__ for b in bc.chain])

app.run(host="0.0.0.0", port=5000)
