from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

NODE_API = "http://127.0.0.1:5000"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/stats")
def stats():

    try:

        chain = requests.get(
            f"{NODE_API}/chain"
        ).json()

        miner = requests.get(
            f"{NODE_API}/miner"
        ).json()

        peers = requests.get(
            f"{NODE_API}/peers"
        ).json()

        mempool = requests.get(
            f"{NODE_API}/mempool"
        ).json()

        latest_block = chain["chain"][-1]

        return jsonify({

            "height":
            len(chain["chain"]) - 1,

            "latest_hash":
            latest_block["hash"],

            "difficulty":
            latest_block.get(
                "difficulty",
                1
            ),

            "pending_txs":
            len(
                mempool.get(
                    "transactions",
                    []
                )
            ),

            "hashrate":
            miner.get(
                "hashrate",
                0
            ),

            "miners":
            miner.get(
                "workers",
                0
            ),

            "peers":
            len(
                peers.get(
                    "peers",
                    []
                )
            ),

            "supply":
            chain.get(
                "supply",
                0
            ),

            "latest_block":
            latest_block
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

@app.route("/api/blocks")
def blocks():

    try:

        chain = requests.get(
            f"{NODE_API}/chain"
        ).json()

        blocks = chain["chain"][-20:]

        return jsonify(blocks[::-1])

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

@app.route("/api/mempool")
def mempool():

    try:

        txs = requests.get(
            f"{NODE_API}/mempool"
        ).json()

        return jsonify(txs)

    except Exception as e:

        return jsonify({
            "error": str(e)
        })

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080
    )
