@app.route("/peers", methods=["GET"])
def get_peers():
    return jsonify(list(app.p2p.peers))


@app.route("/add_peer", methods=["POST"])
def add_peer():
    data = request.json

    peer = data.get("peer")

    if not peer:
        return jsonify({"error": "Missing peer"}), 400

    app.p2p.add_peer(peer)

    return jsonify({
        "message": "Peer added",
        "peer": peer
    })


@app.route("/sync", methods=["GET"])
def sync():
    app.p2p.sync_chain()

    return jsonify({
        "message": "Chain synced",
        "length": len(app.blockchain.chain)
    })
