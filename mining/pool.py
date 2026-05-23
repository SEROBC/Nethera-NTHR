# =========================================================
# Nethera-NTHR
# mining/pool.py
# Advanced Mining Pool + Stratum-Style Server
# =========================================================

import time
import json
import socket
import random
import hashlib
import threading

# =========================================================
# CONFIG
# =========================================================

POOL_HOST = "0.0.0.0"
POOL_PORT = 3333

POOL_FEE = 0.01

SHARE_DIFFICULTY = 3

MIN_PAYOUT = 1.0

BLOCK_REWARD = 50

BUFFER_SIZE = 65536

# =========================================================
# MINING POOL
# =========================================================

class MiningPool:

    def __init__(
        self,
        blockchain=None
    ):

        self.blockchain = blockchain

        # -----------------------------------------
        # Miners
        # -----------------------------------------

        self.miners = {}

        # -----------------------------------------
        # Shares
        # -----------------------------------------

        self.shares = {}

        # -----------------------------------------
        # Pending payouts
        # -----------------------------------------

        self.balances = {}

        # -----------------------------------------
        # Current jobs
        # -----------------------------------------

        self.jobs = {}

        # -----------------------------------------
        # Stats
        # -----------------------------------------

        self.total_hashrate = 0

        self.total_shares = 0

        self.blocks_found = 0

        self.running = False

        self.lock = threading.Lock()

    # =====================================================
    # START POOL
    # =====================================================

    def start(self):

        self.running = True

        threading.Thread(
            target=self.pool_server,
            daemon=True
        ).start()

        threading.Thread(
            target=self.job_loop,
            daemon=True
        ).start()

        threading.Thread(
            target=self.payout_loop,
            daemon=True
        ).start()

        print(
            f"[POOL] Started on "
            f"{POOL_HOST}:{POOL_PORT}"
        )

    # =====================================================
    # SERVER
    # =====================================================

    def pool_server(self):

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
            (POOL_HOST, POOL_PORT)
        )

        server.listen(256)

        while self.running:

            try:

                conn, addr = (
                    server.accept()
                )

                threading.Thread(

                    target=
                    self.handle_miner,

                    args=(
                        conn,
                        addr
                    ),

                    daemon=True

                ).start()

            except Exception as e:

                print(
                    "[POOL SERVER ERROR]",
                    e
                )

    # =====================================================
    # HANDLE MINER
    # =====================================================

    def handle_miner(
        self,
        conn,
        addr
    ):

        ip = addr[0]

        print(
            f"[MINER CONNECTED] {ip}"
        )

        try:

            while True:

                raw = conn.recv(
                    BUFFER_SIZE
                )

                if not raw:
                    break

                data = json.loads(
                    raw.decode()
                )

                msg_type = data.get(
                    "type"
                )

                # ---------------------------------
                # Miner auth
                # ---------------------------------

                if msg_type == "login":

                    wallet = data.get(
                        "wallet"
                    )

                    worker = data.get(
                        "worker",
                        "worker"
                    )

                    miner_id = (
                        f"{wallet}.{worker}"
                    )

                    with self.lock:

                        self.miners[
                            miner_id
                        ] = {

                            "wallet":
                            wallet,

                            "worker":
                            worker,

                            "ip":
                            ip,

                            "last_seen":
                            time.time(),

                            "hashrate":
                            0
                        }

                    self.send_job(
                        conn,
                        miner_id
                    )

                # ---------------------------------
                # Share submission
                # ---------------------------------

                elif msg_type == "submit":

                    self.process_share(
                        conn,
                        data
                    )

                # ---------------------------------
                # Stats update
                # ---------------------------------

                elif msg_type == "stats":

                    miner_id = data.get(
                        "miner_id"
                    )

                    hashrate = data.get(
                        "hashrate",
                        0
                    )

                    with self.lock:

                        if miner_id in (
                            self.miners
                        ):

                            self.miners[
                                miner_id
                            ][
                                "hashrate"
                            ] = hashrate

                            self.miners[
                                miner_id
                            ][
                                "last_seen"
                            ] = time.time()

        except Exception as e:

            print(
                "[MINER ERROR]",
                e
            )

        finally:

            conn.close()

    # =====================================================
    # CREATE JOB
    # =====================================================

    def create_job(self):

        previous_hash = "0" * 64

        if (
            self.blockchain
            and
            self.blockchain.chain
        ):

            previous_hash = (
                self.blockchain.chain[-1]
                ["hash"]
            )

        job = {

            "job_id":
            hashlib.sha256(

                str(time.time())
                .encode()

            ).hexdigest(),

            "previous_hash":
            previous_hash,

            "difficulty":
            SHARE_DIFFICULTY,

            "timestamp":
            time.time(),

            "transactions":
            []
        }

        return job

    # =====================================================
    # SEND JOB
    # =====================================================

    def send_job(
        self,
        conn,
        miner_id
    ):

        job = self.create_job()

        with self.lock:

            self.jobs[
                miner_id
            ] = job

        payload = {

            "type":
            "job",

            "job":
            job
        }

        conn.sendall(
            json.dumps(payload)
            .encode()
        )

    # =====================================================
    # PROCESS SHARE
    # =====================================================

    def process_share(
        self,
        conn,
        data
    ):

        miner_id = data.get(
            "miner_id"
        )

        nonce = data.get(
            "nonce"
        )

        result_hash = data.get(
            "hash"
        )

        if miner_id not in (
            self.jobs
        ):

            return

        job = self.jobs[
            miner_id
        ]

        # -----------------------------------------
        # Validate share
        # -----------------------------------------

        valid = self.validate_share(

            job,
            nonce,
            result_hash

        )

        if not valid:

            conn.sendall(

                json.dumps({

                    "type":
                    "reject"

                }).encode()

            )

            return

        # -----------------------------------------
        # Accept share
        # -----------------------------------------

        with self.lock:

            self.total_shares += 1

            self.shares[
                miner_id
            ] = (

                self.shares.get(
                    miner_id,
                    0
                ) + 1

            )

        conn.sendall(

            json.dumps({

                "type":
                "accept"

            }).encode()

        )

        # -----------------------------------------
        # Full block found
        # -----------------------------------------

        if result_hash.startswith(
            "0" * 5
        ):

            print(
                f"[BLOCK FOUND] "
                f"{miner_id}"
            )

            self.blocks_found += 1

            self.reward_miners()

    # =====================================================
    # VALIDATE SHARE
    # =====================================================

    def validate_share(
        self,
        job,
        nonce,
        result_hash
    ):

        payload = (

            str(job)
            +
            str(nonce)

        ).encode()

        expected = hashlib.sha256(
            payload
        ).hexdigest()

        if expected != result_hash:

            return False

        target = (
            "0"
            * SHARE_DIFFICULTY
        )

        return result_hash.startswith(
            target
        )

    # =====================================================
    # REWARD MINERS
    # =====================================================

    def reward_miners(self):

        with self.lock:

            total_shares = sum(
                self.shares.values()
            )

            if total_shares <= 0:

                return

            reward_pool = (

                BLOCK_REWARD
                * (1 - POOL_FEE)

            )

            for miner_id, shares in (
                self.shares.items()
            ):

                ratio = (
                    shares
                    / total_shares
                )

                reward = (
                    reward_pool
                    * ratio
                )

                wallet = (
                    self.miners[
                        miner_id
                    ]["wallet"]
                )

                self.balances[
                    wallet
                ] = (

                    self.balances.get(
                        wallet,
                        0
                    ) + reward

                )

            # Reset shares
            self.shares = {}

    # =====================================================
    # PAYOUT LOOP
    # =====================================================

    def payout_loop(self):

        while self.running:

            try:

                with self.lock:

                    for wallet, balance in list(

                        self.balances.items()

                    ):

                        if balance >= (
                            MIN_PAYOUT
                        ):

                            print(

                                f"[PAYOUT] "
                                f"{wallet} "
                                f"{balance:.4f} NTHR"

                            )

                            # Real TX would go here

                            self.balances[
                                wallet
                            ] = 0

                time.sleep(60)

            except Exception as e:

                print(
                    "[PAYOUT ERROR]",
                    e
                )

                time.sleep(5)

    # =====================================================
    # JOB LOOP
    # =====================================================

    def job_loop(self):

        while self.running:

            try:

                # Update total hashrate
                total = 0

                with self.lock:

                    for miner in (
                        self.miners.values()
                    ):

                        total += miner.get(
                            "hashrate",
                            0
                        )

                self.total_hashrate = total

                time.sleep(10)

            except Exception as e:

                print(
                    "[JOB LOOP ERROR]",
                    e
                )

    # =====================================================
    # POOL STATS
    # =====================================================

    def stats(self):

        with self.lock:

            return {

                "miners":
                len(self.miners),

                "pool_hashrate":
                self.total_hashrate,

                "shares":
                self.total_shares,

                "blocks_found":
                self.blocks_found,

                "balances":
                self.balances
            }

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    pool = MiningPool()

    pool.start()

    while True:

        time.sleep(5)

        print(
            json.dumps(
                pool.stats(),
                indent=2
            )
        )
