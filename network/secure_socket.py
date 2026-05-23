# =========================================================
# Nethera-NTHR
# network/secure_socket.py
# Advanced Secure P2P Socket Layer
# TLS + Signed Handshakes + Peer Reputation
# =========================================================

import socket
import ssl
import json
import time
import hashlib
import threading
import traceback

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey
)

from cryptography.hazmat.primitives import serialization

# =========================================================
# CONFIG
# =========================================================

BUFFER_SIZE = 65536

SOCKET_TIMEOUT = 15

PING_INTERVAL = 30

MAX_MESSAGE_SIZE = 5 * 1024 * 1024

MAX_REPUTATION = 100

MIN_REPUTATION = -100

BAN_THRESHOLD = -25

# =========================================================
# SECURE SOCKET ENGINE
# =========================================================

class SecureSocketNode:

    def __init__(
        self,
        host="0.0.0.0",
        port=6000,
        certfile=None,
        keyfile=None
    ):

        self.host = host
        self.port = port

        self.certfile = certfile
        self.keyfile = keyfile

        # -----------------------------------------
        # Peer database
        # -----------------------------------------

        self.peers = {}

        # -----------------------------------------
        # Reputation system
        # -----------------------------------------

        self.reputation = {}

        # -----------------------------------------
        # Banned peers
        # -----------------------------------------

        self.banned = set()

        # -----------------------------------------
        # Running
        # -----------------------------------------

        self.running = False

        # -----------------------------------------
        # Generate node identity
        # -----------------------------------------

        self.private_key = (
            Ed25519PrivateKey.generate()
        )

        self.public_key = (
            self.private_key.public_key()
        )

        self.node_id = (
            self.generate_node_id()
        )

        # -----------------------------------------
        # Lock
        # -----------------------------------------

        self.lock = threading.Lock()

    # =====================================================
    # NODE ID
    # =====================================================

    def generate_node_id(self):

        pub = self.public_key.public_bytes(

            encoding=
            serialization.Encoding.Raw,

            format=
            serialization.PublicFormat.Raw
        )

        return hashlib.sha256(
            pub
        ).hexdigest()

    # =====================================================
    # START SERVER
    # =====================================================

    def start(self):

        self.running = True

        threading.Thread(
            target=self.server_loop,
            daemon=True
        ).start()

        threading.Thread(
            target=self.ping_loop,
            daemon=True
        ).start()

        print(
            f"[SECURE SOCKET] "
            f"Listening on "
            f"{self.host}:{self.port}"
        )

    # =====================================================
    # TLS CONTEXT
    # =====================================================

    def create_tls_context(self):

        context = ssl.SSLContext(
            ssl.PROTOCOL_TLS_SERVER
        )

        context.check_hostname = False

        context.verify_mode = (
            ssl.CERT_NONE
        )

        if (
            self.certfile
            and
            self.keyfile
        ):

            context.load_cert_chain(
                self.certfile,
                self.keyfile
            )

        return context

    # =====================================================
    # SERVER LOOP
    # =====================================================

    def server_loop(self):

        context = self.create_tls_context()

        server = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        server.bind(
            (self.host, self.port)
        )

        server.listen(128)

        while self.running:

            try:

                client, addr = (
                    server.accept()
                )

                ip = addr[0]

                # ---------------------------------
                # Ban check
                # ---------------------------------

                if ip in self.banned:

                    client.close()

                    continue

                tls_client = (
                    context.wrap_socket(
                        client,
                        server_side=True
                    )
                )

                tls_client.settimeout(
                    SOCKET_TIMEOUT
                )

                threading.Thread(

                    target=
                    self.handle_client,

                    args=(
                        tls_client,
                        addr
                    ),

                    daemon=True

                ).start()

            except Exception as e:

                print(
                    "[SOCKET ERROR]",
                    e
                )

    # =====================================================
    # HANDLE CLIENT
    # =====================================================

    def handle_client(
        self,
        conn,
        addr
    ):

        ip = addr[0]

        try:

            raw = conn.recv(
                BUFFER_SIZE
            )

            if not raw:

                return

            if len(raw) > (
                MAX_MESSAGE_SIZE
            ):

                self.penalize_peer(
                    ip,
                    20
                )

                return

            message = json.loads(
                raw.decode()
            )

            # ---------------------------------
            # Verify signed message
            # ---------------------------------

            if not self.verify_packet(
                message
            ):

                self.penalize_peer(
                    ip,
                    10
                )

                return

            # ---------------------------------
            # Successful peer
            # ---------------------------------

            self.reward_peer(ip)

            # ---------------------------------
            # Register peer
            # ---------------------------------

            peer_id = message.get(
                "node_id"
            )

            with self.lock:

                self.peers[
                    peer_id
                ] = {

                    "ip":
                    ip,

                    "last_seen":
                    time.time(),

                    "public_key":
                    message.get(
                        "public_key"
                    )
                }

            # ---------------------------------
            # Handle message types
            # ---------------------------------

            msg_type = message.get(
                "type"
            )

            if msg_type == "ping":

                self.send_packet(

                    conn,

                    {
                        "type":
                        "pong",

                        "timestamp":
                        time.time()
                    }

                )

            elif msg_type == "message":

                print(
                    "[P2P MESSAGE]",
                    message.get(
                        "data"
                    )
                )

            elif msg_type == "peer_list":

                print(
                    "[PEERS]",
                    message.get(
                        "peers"
                    )
                )

        except Exception as e:

            self.penalize_peer(
                ip,
                5
            )

            print(
                "[CLIENT ERROR]",
                e
            )

        finally:

            try:

                conn.close()
            except:
                pass

    # =====================================================
    # CONNECT TO PEER
    # =====================================================

    def connect_peer(
        self,
        host,
        port,
        message
    ):

        try:

            context = ssl.create_default_context()

            context.check_hostname = False

            context.verify_mode = (
                ssl.CERT_NONE
            )

            sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            sock.settimeout(
                SOCKET_TIMEOUT
            )

            wrapped = (
                context.wrap_socket(
                    sock,
                    server_hostname=host
                )
            )

            wrapped.connect(
                (host, port)
            )

            signed = (
                self.sign_packet(
                    message
                )
            )

            self.send_packet(
                wrapped,
                signed
            )

            response = wrapped.recv(
                BUFFER_SIZE
            )

            if response:

                try:

                    data = json.loads(
                        response.decode()
                    )

                    return data

                except:

                    return None

            wrapped.close()

        except Exception as e:

            print(
                "[PEER CONNECT ERROR]",
                e
            )

        return None

    # =====================================================
    # SEND PACKET
    # =====================================================

    def send_packet(
        self,
        conn,
        packet
    ):

        data = json.dumps(
            packet
        ).encode()

        conn.sendall(data)

    # =====================================================
    # SIGN PACKET
    # =====================================================

    def sign_packet(
        self,
        packet
    ):

        packet["node_id"] = (
            self.node_id
        )

        packet["timestamp"] = (
            time.time()
        )

        pub = self.public_key.public_bytes(

            encoding=
            serialization.Encoding.Raw,

            format=
            serialization.PublicFormat.Raw
        )

        packet["public_key"] = (
            pub.hex()
        )

        payload = json.dumps(

            packet,
            sort_keys=True

        ).encode()

        signature = (
            self.private_key.sign(
                payload
            )
        )

        packet["signature"] = (
            signature.hex()
        )

        return packet

    # =====================================================
    # VERIFY PACKET
    # =====================================================

    def verify_packet(
        self,
        packet
    ):

        try:

            signature = bytes.fromhex(
                packet.pop(
                    "signature"
                )
            )

            pubkey_hex = packet.get(
                "public_key"
            )

            if not pubkey_hex:

                return False

            pubkey = (
                Ed25519PublicKey
                .from_public_bytes(
                    bytes.fromhex(
                        pubkey_hex
                    )
                )
            )

            payload = json.dumps(

                packet,
                sort_keys=True

            ).encode()

            pubkey.verify(
                signature,
                payload
            )

            return True

        except Exception:

            return False

    # =====================================================
    # PEER REPUTATION
    # =====================================================

    def reward_peer(
        self,
        ip,
        amount=1
    ):

        with self.lock:

            current = (
                self.reputation.get(
                    ip,
                    0
                )
            )

            current += amount

            current = min(
                current,
                MAX_REPUTATION
            )

            self.reputation[ip] = (
                current
            )

    # =====================================================
    # PENALIZE PEER
    # =====================================================

    def penalize_peer(
        self,
        ip,
        amount=1
    ):

        with self.lock:

            current = (
                self.reputation.get(
                    ip,
                    0
                )
            )

            current -= amount

            current = max(
                current,
                MIN_REPUTATION
            )

            self.reputation[ip] = (
                current
            )

            if current <= (
                BAN_THRESHOLD
            ):

                self.banned.add(ip)

                print(
                    f"[BANNED] {ip}"
                )

    # =====================================================
    # PING LOOP
    # =====================================================

    def ping_loop(self):

        while self.running:

            try:

                with self.lock:

                    peers = list(
                        self.peers.values()
                    )

                for peer in peers:

                    ip = peer["ip"]

                    try:

                        self.connect_peer(

                            ip,
                            self.port,

                            {
                                "type":
                                "ping"
                            }

                        )

                    except:

                        self.penalize_peer(
                            ip,
                            1
                        )

                time.sleep(
                    PING_INTERVAL
                )

            except Exception as e:

                print(
                    "[PING LOOP ERROR]",
                    e
                )

    # =====================================================
    # PEER LIST
    # =====================================================

    def get_peers(self):

        with self.lock:

            return self.peers

    # =====================================================
    # REPUTATION TABLE
    # =====================================================

    def get_reputation(self):

        with self.lock:

            return self.reputation

    # =====================================================
    # STATS
    # =====================================================

    def stats(self):

        with self.lock:

            return {

                "node_id":
                self.node_id,

                "connected_peers":
                len(self.peers),

                "banned_peers":
                len(self.banned),

                "reputation_entries":
                len(self.reputation),

                "running":
                self.running
            }

# =========================================================
# MAIN TEST
# =========================================================

if __name__ == "__main__":

    node = SecureSocketNode(
        host="0.0.0.0",
        port=6000
    )

    node.start()

    while True:

        time.sleep(5)

        print(node.stats())
