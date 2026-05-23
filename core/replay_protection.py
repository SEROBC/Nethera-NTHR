# =========================================================
# Nethera-NTHR
# core/replay_protection.py
# Advanced Replay Protection + Nonce Security System
# =========================================================

import time
import hashlib
import threading

# =========================================================
# CONFIG
# =========================================================

# Mainnet/Testnet chain identifier
CHAIN_ID = "NTHR-MAINNET"

# Allowed timestamp drift (seconds)
MAX_TIME_DRIFT = 300

# Nonce cache cleanup interval
CLEANUP_INTERVAL = 120

# Maximum cached TX hashes
MAX_CACHE_SIZE = 100000

# Transaction expiration
TX_EXPIRATION = 3600

# =========================================================
# REPLAY PROTECTION ENGINE
# =========================================================

class ReplayProtection:

    def __init__(self):

        # -----------------------------------------
        # TX replay cache
        # -----------------------------------------

        self.tx_cache = {}

        # -----------------------------------------
        # Nonce tracking
        # address -> latest nonce
        # -----------------------------------------

        self.address_nonces = {}

        # -----------------------------------------
        # Lock
        # -----------------------------------------

        self.lock = threading.Lock()

        # -----------------------------------------
        # Start cleaner
        # -----------------------------------------

        cleaner = threading.Thread(
            target=self.cleanup_loop,
            daemon=True
        )

        cleaner.start()

    # =====================================================
    # GENERATE TX HASH
    # =====================================================

    def generate_tx_hash(
        self,
        tx
    ):

        tx_data = {

            "sender":
            tx.get("sender"),

            "receiver":
            tx.get("receiver"),

            "amount":
            tx.get("amount"),

            "fee":
            tx.get("fee", 0),

            "nonce":
            tx.get("nonce"),

            "timestamp":
            tx.get("timestamp"),

            "chain_id":
            tx.get("chain_id")
        }

        tx_string = str(
            sorted(tx_data.items())
        )

        return hashlib.sha256(
            tx_string.encode()
        ).hexdigest()

    # =====================================================
    # VALIDATE CHAIN ID
    # =====================================================

    def validate_chain_id(
        self,
        tx
    ):

        chain_id = tx.get(
            "chain_id"
        )

        if not chain_id:

            return (
                False,
                "Missing chain_id"
            )

        if chain_id != CHAIN_ID:

            return (
                False,
                "Invalid chain_id"
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # VALIDATE TIMESTAMP
    # =====================================================

    def validate_timestamp(
        self,
        tx
    ):

        timestamp = tx.get(
            "timestamp"
        )

        if timestamp is None:

            return (
                False,
                "Missing timestamp"
            )

        now = time.time()

        drift = abs(
            now - timestamp
        )

        if drift > MAX_TIME_DRIFT:

            return (
                False,
                "Transaction expired"
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # VALIDATE NONCE
    # =====================================================

    def validate_nonce(
        self,
        tx
    ):

        sender = tx.get(
            "sender"
        )

        nonce = tx.get(
            "nonce"
        )

        if nonce is None:

            return (
                False,
                "Missing nonce"
            )

        try:

            nonce = int(nonce)

        except:

            return (
                False,
                "Invalid nonce"
            )

        if nonce < 0:

            return (
                False,
                "Negative nonce"
            )

        with self.lock:

            current = (
                self.address_nonces.get(
                    sender,
                    -1
                )
            )

            # Must increase
            if nonce <= current:

                return (
                    False,
                    f"Replay detected "
                    f"(nonce={nonce})"
                )

        return (
            True,
            "OK"
        )

    # =====================================================
    # CHECK REPLAY CACHE
    # =====================================================

    def check_replay(
        self,
        tx
    ):

        tx_hash = self.generate_tx_hash(
            tx
        )

        with self.lock:

            if tx_hash in self.tx_cache:

                return (
                    False,
                    "Replay transaction"
                )

        return (
            True,
            tx_hash
        )

    # =====================================================
    # REGISTER TX
    # =====================================================

    def register_transaction(
        self,
        tx
    ):

        sender = tx.get(
            "sender"
        )

        nonce = int(
            tx.get("nonce")
        )

        tx_hash = self.generate_tx_hash(
            tx
        )

        now = time.time()

        with self.lock:

            # Save nonce
            self.address_nonces[
                sender
            ] = nonce

            # Save replay cache
            self.tx_cache[
                tx_hash
            ] = {

                "timestamp":
                now,

                "sender":
                sender,

                "nonce":
                nonce
            }

            # Trim cache
            if len(self.tx_cache) > (
                MAX_CACHE_SIZE
            ):

                oldest = sorted(
                    self.tx_cache.items(),
                    key=lambda x:
                    x[1]["timestamp"]
                )[:1000]

                for k, _ in oldest:

                    del self.tx_cache[k]

    # =====================================================
    # FULL VALIDATION
    # =====================================================

    def validate_transaction(
        self,
        tx
    ):

        # -----------------------------------------
        # Chain ID
        # -----------------------------------------

        valid, msg = (
            self.validate_chain_id(tx)
        )

        if not valid:

            return (
                False,
                msg
            )

        # -----------------------------------------
        # Timestamp
        # -----------------------------------------

        valid, msg = (
            self.validate_timestamp(tx)
        )

        if not valid:

            return (
                False,
                msg
            )

        # -----------------------------------------
        # Nonce
        # -----------------------------------------

        valid, msg = (
            self.validate_nonce(tx)
        )

        if not valid:

            return (
                False,
                msg
            )

        # -----------------------------------------
        # Replay cache
        # -----------------------------------------

        valid, msg = (
            self.check_replay(tx)
        )

        if not valid:

            return (
                False,
                msg
            )

        return (
            True,
            "OK"
        )

    # =====================================================
    # CLEANUP LOOP
    # =====================================================

    def cleanup_loop(self):

        while True:

            try:

                now = time.time()

                expired = []

                with self.lock:

                    for tx_hash, data in (
                        self.tx_cache.items()
                    ):

                        age = (
                            now
                            - data["timestamp"]
                        )

                        if age > TX_EXPIRATION:

                            expired.append(
                                tx_hash
                            )

                    for tx_hash in expired:

                        del self.tx_cache[
                            tx_hash
                        ]

                time.sleep(
                    CLEANUP_INTERVAL
                )

            except Exception as e:

                print(
                    "[REPLAY CLEANER ERROR]",
                    e
                )

                time.sleep(5)

    # =====================================================
    # GET NONCE
    # =====================================================

    def get_next_nonce(
        self,
        address
    ):

        with self.lock:

            current = (
                self.address_nonces.get(
                    address,
                    -1
                )
            )

            return current + 1

    # =====================================================
    # STATS
    # =====================================================

    def stats(self):

        with self.lock:

            return {

                "chain_id":
                CHAIN_ID,

                "tracked_wallets":
                len(
                    self.address_nonces
                ),

                "cached_transactions":
                len(
                    self.tx_cache
                ),

                "max_time_drift":
                MAX_TIME_DRIFT,

                "tx_expiration":
                TX_EXPIRATION
            }

# =========================================================
# GLOBAL INSTANCE
# =========================================================

replay_protection = ReplayProtection()
