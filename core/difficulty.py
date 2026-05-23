# =========================================================
# Nethera-NTHR
# core/difficulty.py
# Advanced Dynamic Difficulty Retargeting Engine
# =========================================================

import time
import math

# =========================================================
# CONFIG
# =========================================================

# Target seconds per block
TARGET_BLOCK_TIME = 30

# How many blocks before retarget
RETARGET_INTERVAL = 10

# Minimum difficulty
MIN_DIFFICULTY = 2

# Maximum difficulty
MAX_DIFFICULTY = 12

# Max difficulty adjustment factor
MAX_ADJUST_UP = 4
MAX_ADJUST_DOWN = 0.25

# Smoothing factor
EMA_ALPHA = 0.25

# =========================================================
# DIFFICULTY ENGINE
# =========================================================

class DifficultyManager:

    def __init__(self):

        self.target_block_time = (
            TARGET_BLOCK_TIME
        )

        self.retarget_interval = (
            RETARGET_INTERVAL
        )

        self.min_difficulty = (
            MIN_DIFFICULTY
        )

        self.max_difficulty = (
            MAX_DIFFICULTY
        )

    # =====================================================
    # GET CURRENT DIFFICULTY
    # =====================================================

    def get_current_difficulty(
        self,
        blockchain
    ):

        # -----------------------------------------
        # Genesis phase
        # -----------------------------------------

        if len(blockchain.chain) < 2:

            return self.min_difficulty

        latest = blockchain.chain[-1]

        return latest.get(
            "difficulty",
            self.min_difficulty
        )

    # =====================================================
    # RETARGET CHECK
    # =====================================================

    def should_retarget(
        self,
        blockchain
    ):

        height = len(blockchain.chain)

        return (
            height %
            self.retarget_interval
        ) == 0

    # =====================================================
    # CALCULATE NEXT DIFFICULTY
    # =====================================================

    def calculate_next_difficulty(
        self,
        blockchain
    ):

        # -----------------------------------------
        # Genesis protection
        # -----------------------------------------

        if len(blockchain.chain) <= (
            self.retarget_interval
        ):

            return self.min_difficulty

        latest = blockchain.chain[-1]

        current_difficulty = latest.get(
            "difficulty",
            self.min_difficulty
        )

        # -----------------------------------------
        # Recent window
        # -----------------------------------------

        recent_blocks = blockchain.chain[
            -self.retarget_interval:
        ]

        first_block = recent_blocks[0]
        last_block = recent_blocks[-1]

        actual_time = (
            last_block["timestamp"]
            - first_block["timestamp"]
        )

        expected_time = (
            self.target_block_time
            * self.retarget_interval
        )

        # -----------------------------------------
        # Safety
        # -----------------------------------------

        if actual_time <= 0:

            actual_time = 1

        # -----------------------------------------
        # Ratio
        # -----------------------------------------

        ratio = (
            expected_time / actual_time
        )

        # Clamp
        ratio = max(
            MAX_ADJUST_DOWN,
            min(
                MAX_ADJUST_UP,
                ratio
            )
        )

        # -----------------------------------------
        # EMA smoothing
        # -----------------------------------------

        smoothed_ratio = (
            (EMA_ALPHA * ratio)
            +
            ((1 - EMA_ALPHA) * 1)
        )

        # -----------------------------------------
        # New difficulty
        # -----------------------------------------

        new_difficulty = (
            current_difficulty
            * smoothed_ratio
        )

        # Round
        new_difficulty = round(
            new_difficulty
        )

        # Clamp bounds
        new_difficulty = max(
            self.min_difficulty,
            min(
                self.max_difficulty,
                new_difficulty
            )
        )

        return new_difficulty

    # =====================================================
    # VALIDATE POW
    # =====================================================

    def validate_pow(
        self,
        block
    ):

        difficulty = block.get(
            "difficulty",
            self.min_difficulty
        )

        block_hash = block.get(
            "hash",
            ""
        )

        target = "0" * difficulty

        return block_hash.startswith(
            target
        )

    # =====================================================
    # CALCULATE NETWORK HASHRATE
    # =====================================================

    def calculate_network_hashrate(
        self,
        blockchain
    ):

        if len(blockchain.chain) < 2:

            return 0

        sample_size = min(
            20,
            len(blockchain.chain) - 1
        )

        blocks = blockchain.chain[
            -sample_size:
        ]

        total_time = 0
        total_difficulty = 0

        for i in range(
            1,
            len(blocks)
        ):

            prev = blocks[i - 1]
            curr = blocks[i]

            block_time = (
                curr["timestamp"]
                - prev["timestamp"]
            )

            if block_time <= 0:
                continue

            total_time += block_time

            total_difficulty += (
                curr.get(
                    "difficulty",
                    self.min_difficulty
                )
            )

        if total_time <= 0:

            return 0

        avg_difficulty = (
            total_difficulty
            / sample_size
        )

        # Estimated hashes
        estimated_hashes = (
            2 ** avg_difficulty
        )

        return round(
            estimated_hashes
            / (total_time / sample_size),
            2
        )

    # =====================================================
    # CHAIN HEALTH
    # =====================================================

    def chain_health(
        self,
        blockchain
    ):

        if len(blockchain.chain) < 2:

            return {
                "healthy": True,
                "avg_block_time": 0,
                "difficulty":
                self.min_difficulty,
                "hashrate": 0
            }

        sample = blockchain.chain[-20:]

        times = []

        for i in range(
            1,
            len(sample)
        ):

            dt = (
                sample[i]["timestamp"]
                - sample[i - 1]["timestamp"]
            )

            times.append(dt)

        avg_time = (
            sum(times)
            / len(times)
        )

        latest = blockchain.chain[-1]

        difficulty = latest.get(
            "difficulty",
            self.min_difficulty
        )

        hashrate = (
            self.calculate_network_hashrate(
                blockchain
            )
        )

        healthy = (
            avg_time <
            self.target_block_time * 3
        )

        return {

            "healthy": healthy,

            "avg_block_time":
            round(avg_time, 2),

            "difficulty":
            difficulty,

            "hashrate":
            hashrate
        }

# =========================================================
# GLOBAL INSTANCE
# =========================================================

difficulty_manager = DifficultyManager()
