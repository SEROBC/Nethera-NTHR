from node.node import app
from core.blockchain import Blockchain
from network.p2p import P2PNode

import threading
import os

blockchain = Blockchain()

P2P_PORT = int(os.getenv("P2P_PORT", 6000))
API_PORT = int(os.getenv("PORT", 5000))

p2p = P2PNode(blockchain, port=P2P_PORT)

app.blockchain = blockchain
app.p2p = p2p

# -------------------------
# START P2P NETWORK
# -------------------------

thread = threading.Thread(target=p2p.start)

thread.daemon = True

thread.start()

print(f"[API] Running on {API_PORT}")
print(f"[P2P] Running on {P2P_PORT}")

# -------------------------
# START FLASK
# -------------------------

app.run(
    host="0.0.0.0",
    port=API_PORT
)
