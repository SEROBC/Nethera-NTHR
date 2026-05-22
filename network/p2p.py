import socket
import threading
import json
import requests
import time

PEERS_FILE = "network/peers.json"

class P2PNode:
    def __init__(self, blockchain, host="0.0.0.0", port=6000):
        self.blockchain = blockchain
        self.host = host
        self.port = port
        self.peers = set()

        self.load_peers()

    # -------------------------
    # PEER STORAGE
    # -------------------------

    def load_peers(self):
        try:
            with open(PEERS_FILE, "r") as f:
                peers = json.load(f)
                self.peers = set(peers)
        except:
            self.peers = set()

    def save_peers(self):
        with open(PEERS_FILE, "w") as f:
            json.dump(list(self.peers), f, indent=4)

    # -------------------------
    # SERVER
    # -------------------------

    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((self.host, self.port))
        server.listen(5)

        print(f"[P2P] Listening on {self.host}:{self.port}")

        while True:
            client, addr = server.accept()

            thread = threading.Thread(
                target=self.handle_client,
                args=(client,)
            )
            thread.start()

    def handle_client(self, client):
        try:
            data = client.recv(65536).decode()

            if not data:
                return

            message = json.loads(data)

            msg_type = message.get("type")

            # -------------------------
            # NEW TRANSACTION
            # -------------------------

            if msg_type == "tx":
                tx = message["data"]

                exists = tx in self.blockchain.pending_transactions

                if not exists:
                    self.blockchain.pending_transactions.append(tx)

                    print("[P2P] TX received")

                    self.broadcast_transaction(tx)

            # -------------------------
            # NEW BLOCK
            # -------------------------

            elif msg_type == "block":
                block = message["data"]

                latest = self.blockchain.get_latest_block()

                if block["index"] > latest["index"]:
                    self.blockchain.chain.append(block)

                    print("[P2P] Block synced")

                    self.broadcast_block(block)

            # -------------------------
            # CHAIN REQUEST
            # -------------------------

            elif msg_type == "get_chain":
                response = {
                    "type": "chain",
                    "data": self.blockchain.chain
                }

                client.send(json.dumps(response).encode())

            # -------------------------
            # CHAIN RESPONSE
            # -------------------------

            elif msg_type == "chain":
                incoming_chain = message["data"]

                if len(incoming_chain) > len(self.blockchain.chain):
                    self.blockchain.chain = incoming_chain

                    print("[P2P] Chain updated from peer")

        except Exception as e:
            print("[P2P ERROR]", e)

        finally:
            client.close()

    # -------------------------
    # SEND MESSAGE
    # -------------------------

    def send_message(self, peer, message):
        try:
            host, port = peer.split(":")

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            s.settimeout(5)

            s.connect((host, int(port)))

            s.send(json.dumps(message).encode())

            s.close()

        except Exception as e:
            print(f"[PEER FAIL] {peer} -> {e}")

    # -------------------------
    # BROADCAST TX
    # -------------------------

    def broadcast_transaction(self, tx):
        message = {
            "type": "tx",
            "data": tx
        }

        for peer in self.peers:
            self.send_message(peer, message)

    # -------------------------
    # BROADCAST BLOCK
    # -------------------------

    def broadcast_block(self, block):
        message = {
            "type": "block",
            "data": block
        }

        for peer in self.peers:
            self.send_message(peer, message)

    # -------------------------
    # CHAIN SYNC
    # -------------------------

    def sync_chain(self):
        for peer in self.peers:
            try:
                host, port = peer.split(":")

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                s.settimeout(5)

                s.connect((host, int(port)))

                message = {
                    "type": "get_chain"
                }

                s.send(json.dumps(message).encode())

                data = s.recv(999999).decode()

                response = json.loads(data)

                if response["type"] == "chain":
                    incoming = response["data"]

                    if len(incoming) > len(self.blockchain.chain):
                        self.blockchain.chain = incoming

                        print("[SYNC] Chain updated")

                s.close()

            except Exception as e:
                print("[SYNC ERROR]", e)

    # -------------------------
    # ADD PEER
    # -------------------------

    def add_peer(self, peer):
        self.peers.add(peer)
        self.save_peers()

        print(f"[PEER ADDED] {peer}")
