# =========================================================
# Nethera-NTHR
# core/finality.py
# Advanced Chain Finality + Anti-Reorg Protection
# =========================================================

import time
import hashlib
import threading

# =========================================================
# CONFIG
# =========================================================

# Blocks required before irreversible
FINALITY_DEPTH = 12

# Maximum allowed reorg depth
MAX_REORG_DEPTH = 6

# Checkpoint interval
CHECKPOINT_INTERVAL = 50

# Finality voting threshold
FINALITY_THRESHOLD = 0.67

# =========================================================
# FINALITY ENGINE
# =========================================================

class FinalityManager:

    def __init__(self):

        # -----------------------------------------
        # Finalized checkpoints
        # -----------------------------------------

        self.finalized_blocks = {}

        # -----------------------------------------
        # Chain checkpoints
        # -----------------------------------------

        self.checkpoints = {}

        # -----------------------------------------
        # Finality votes
        # -----------------------------------------

        self.votes = {}

        # -----------------------------------------
        # Lock
        # -----------------------------------------

        self.lock = threading.Lock()

    # =====================================================
    # FINALIZED HEIGHT
    # =====================================================

    def get_finalized_height(
        self,
        blockchain
    ):

        height = len(
            blockchain.chain
        ) - 1

        finalized = (
            height
            - FINALITY_DEPTH
        )

        return max(
            0,
            finalized
        )

    # =====================================================
    # FINALIZE BLOCKS
    # =====================================================

    def finalize_blocks(
        self,
        blockchain
    ):

        with self.lock:

            finalized_height = (
                self.get_finalized_height(
                    blockchain
                )
            )

            for block in blockchain.chain:

                index = block["index"]

                if index <= finalized_height:

                    self.finalized_blocks[
                        index
                    ] = {

                        "hash":
                        block["hash"],

                        "timestamp":
                        time.time()
                    }

    # =====================================================
    # IS BLOCK FINALIZED
    # =====================================================

    def is_finalized(
        self,
        block_index
    ):

        return (
            block_index
            in self.finalized_blocks
        )

    # =====================================================
    # GET FINALIZED HASH
    # =====================================================

    def get_finalized_hash(
        self,
        block_index
    ):

        block = (
            self.finalized_blocks.get(
                block_index
            )
        )

        if not block:

            return None

        return block["hash"]

    # =====================================================
    # CHECK REORG SAFETY
    # =====================================================

    def validate_reorg(
        self,
        old_chain,
        new_chain
    ):

        old_height = (
            len(old_chain) - 1
        )

        new_height = (
            len(new_chain) - 1
        )

        # -----------------------------------------
        # Find fork point
        # -----------------------------------------

        fork_index = None

        min_len = min(
            len(old_chain),
            len(new_chain)
        )

        for i in range(min_len):

            if (
                old_chain[i]["hash"]
                !=
                new_chain[i]["hash"]
            ):

                fork_index = i

                break

        # No fork
        if fork_index is None:

            return (
                True,
                "No reorg"
            )

        # -----------------------------------------
        # Reorg depth
        # -----------------------------------------

        reorg_depth = (
            old_height
            - fork_index
        )

        # -----------------------------------------
        # Too deep
        # -----------------------------------------

        if reorg_depth > (
            MAX_REORG_DEPTH
        ):

            return (
                False,
                f"Reorg too deep "
                f"({reorg_depth})"
            )

        # -----------------------------------------
        # Finalized block rewrite
        # -----------------------------------------

        for i in range(
            fork_index,
            old_height + 1
        ):

            if self.is_finalized(i):

                return (
                    False,
                    f"Attempt to rewrite "
                    f"finalized block {i}"
                )

        return (
            True,
            "Reorg accepted"
        )

    # =====================================================
    # CREATE CHECKPOINT
    # =====================================================

    def create_checkpoint(
        self,
        blockchain
    ):

        latest = blockchain.chain[-1]

        index = latest["index"]

        if (
            index %
            CHECKPOINT_INTERVAL
        ) != 0:

            return None

        checkpoint_hash = hashlib.sha256(

            (
                str(index)
                +
                latest["hash"]
            ).encode()

        ).hexdigest()

        checkpoint = {

            "index":
            index,

            "hash":
            latest["hash"],

            "checkpoint_hash":
            checkpoint_hash,

            "timestamp":
            time.time()
        }

        with self.lock:

            self.checkpoints[
                index
            ] = checkpoint

        return checkpoint

    # =====================================================
    # VERIFY CHECKPOINT
    # =====================================================

    def verify_checkpoint(
        self,
        block
    ):

        index = block["index"]

        checkpoint = (
            self.checkpoints.get(
                index
            )
        )

        if not checkpoint:

            return True

        return (
            checkpoint["hash"]
            ==
            block["hash"]
        )

    # =====================================================
    # CUMULATIVE WORK
    # =====================================================

    def cumulative_work(
        self,
        chain
    ):

        total = 0

        for block in chain:

            difficulty = block.get(
                "difficulty",
                1
            )

            total += (
                2 ** difficulty
            )

        return total

    # =====================================================
    # CHOOSE BEST CHAIN
    # =====================================================

    def choose_best_chain(
        self,
        local_chain,
        remote_chain
    ):

        local_work = (
            self.cumulative_work(
                local_chain
            )
        )

        remote_work = (
            self.cumulative_work(
                remote_chain
            )
        )

        if remote_work > local_work:

            valid, reason = (
                self.validate_reorg(
                    local_chain,
                    remote_chain
                )
            )

            if valid:

                return (
                    remote_chain,
                    "Remote chain selected"
                )

            return (
                local_chain,
                reason
            )

        return (
            local_chain,
            "Local chain retained"
        )

    # =====================================================
    # VALIDATE FINALITY
    # =====================================================

    def validate_finality(
        self,
        blockchain
    ):

        try:

            # -------------------------------------
            # Check finalized blocks
            # -------------------------------------

            for index, data in (
                self.finalized_blocks.items()
            ):

                if index >= len(
                    blockchain.chain
                ):

                    return (
                        False,
                        f"Missing finalized "
                        f"block {index}"
                    )

                block = (
                    blockchain.chain[index]
                )

                if (
                    block["hash"]
                    !=
                    data["hash"]
                ):

                    return (
                        False,
                        f"Finalized block "
                        f"tampered {index}"
                    )

            # -------------------------------------
            # Check checkpoints
            # -------------------------------------

            for index, checkpoint in (
                self.checkpoints.items()
            ):

                if index >= len(
                    blockchain.chain
                ):

                    continue

                block = (
                    blockchain.chain[index]
                )

                if (
                    block["hash"]
                    !=
                    checkpoint["hash"]
                ):

                    return (
                        False,
                        f"Checkpoint mismatch "
                        f"{index}"
                    )

            return (
                True,
                "Finality valid"
            )

        except Exception as e:

            return (
                False,
                str(e)
            )

    # =====================================================
    # NETWORK FINALITY VOTES
    # =====================================================

    def add_vote(
        self,
        block_hash,
        peer_id
    ):

        with self.lock:

            if block_hash not in self.votes:

                self.votes[
                    block_hash
                ] = set()

            self.votes[
                block_hash
            ].add(peer_id)

    # =====================================================
    # FINALITY CONFIRMED
    # =====================================================

    def has_finality(
        self,
        block_hash,
        total_peers
    ):

        if total_peers <= 0:

            return False

        votes = len(

            self.votes.get(
                block_hash,
                set()
            )

        )

        ratio = (
            votes / total_peers
        )

        return (
            ratio >= FINALITY_THRESHOLD
        )

    # =====================================================
    # STATS
    # =====================================================

    def stats(self):

        with self.lock:

            return {

                "finalized_blocks":
                len(
                    self.finalized_blocks
                ),

                "checkpoints":
                len(
                    self.checkpoints
                ),

                "vote_sets":
                len(
                    self.votes
                ),

                "finality_depth":
                FINALITY_DEPTH,

                "max_reorg_depth":
                MAX_REORG_DEPTH
            }

# =========================================================
# GLOBAL INSTANCE
# =========================================================

finality_manager = FinalityManager()
