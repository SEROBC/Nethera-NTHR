# =========================================================
# Nethera-NTHR
# defi/liquidity_pool.py
# AMM Exchange + Liquidity System (Uniswap-style)
# =========================================================

import time
import uuid
import threading

# =========================================================
# LIQUIDITY POOL ENGINE
# =========================================================

class LiquidityPool:

    def __init__(
        self,
        token_a="NTHR",
        token_b="USDT"
    ):

        self.token_a = token_a
        self.token_b = token_b

        # -----------------------------------------
        # Reserves
        # -----------------------------------------

        self.reserve_a = 0.0
        self.reserve_b = 0.0

        # -----------------------------------------
        # Liquidity providers
        # wallet -> shares
        # -----------------------------------------

        self.liquidity = {}

        # total LP shares
        self.total_shares = 0.0

        # -----------------------------------------
        # Fee system
        # -----------------------------------------

        self.fee_rate = 0.003  # 0.3%

        # collected fees
        self.fees_a = 0.0
        self.fees_b = 0.0

        # -----------------------------------------
        # Lock
        # -----------------------------------------

        self.lock = threading.Lock()

    # =====================================================
    # ADD LIQUIDITY
    # =====================================================

    def add_liquidity(
        self,
        wallet,
        amount_a,
        amount_b
    ):

        with self.lock:

            # First liquidity sets price
            if self.total_shares == 0:

                shares = (amount_a * amount_b) ** 0.5

            else:

                shares = min(

                    amount_a / self.reserve_a * self.total_shares,

                    amount_b / self.reserve_b * self.total_shares

                )

            self.reserve_a += amount_a
            self.reserve_b += amount_b

            self.liquidity[wallet] = (
                self.liquidity.get(wallet, 0)
                + shares
            )

            self.total_shares += shares

            return {
                "shares": shares,
                "pool_reserve_a": self.reserve_a,
                "pool_reserve_b": self.reserve_b
            }

    # =====================================================
    # REMOVE LIQUIDITY
    # =====================================================

    def remove_liquidity(
        self,
        wallet,
        shares
    ):

        with self.lock:

            if wallet not in self.liquidity:

                return None

            if shares > self.liquidity[wallet]:

                return None

            ratio = shares / self.total_shares

            amount_a = self.reserve_a * ratio
            amount_b = self.reserve_b * ratio

            self.reserve_a -= amount_a
            self.reserve_b -= amount_b

            self.liquidity[wallet] -= shares
            self.total_shares -= shares

            return {
                "amount_a": amount_a,
                "amount_b": amount_b
            }

    # =====================================================
    # GET PRICE
    # =====================================================

    def get_price(self):

        if self.reserve_a == 0:

            return 0

        return self.reserve_b / self.reserve_a

    # =====================================================
    # SWAP A -> B
    # =====================================================

    def swap_a_to_b(self, amount_a_in):

        with self.lock:

            if amount_a_in <= 0:

                return None

            amount_in_with_fee = (
                amount_a_in
                * (1 - self.fee_rate)
            )

            new_a = self.reserve_a + amount_in_with_fee

            new_b = (self.reserve_a * self.reserve_b) / new_a

            amount_b_out = self.reserve_b - new_b

            self.reserve_a += amount_in_with_fee
            self.reserve_b -= amount_b_out

            self.fees_a += amount_a_in * self.fee_rate

            return amount_b_out

    # =====================================================
    # SWAP B -> A
    # =====================================================

    def swap_b_to_a(self, amount_b_in):

        with self.lock:

            if amount_b_in <= 0:

                return None

            amount_in_with_fee = (
                amount_b_in
                * (1 - self.fee_rate)
            )

            new_b = self.reserve_b + amount_in_with_fee

            new_a = (self.reserve_a * self.reserve_b) / new_b

            amount_a_out = self.reserve_a - new_a

            self.reserve_b += amount_in_with_fee
            self.reserve_a -= amount_a_out

            self.fees_b += amount_b_in * self.fee_rate

            return amount_a_out

    # =====================================================
    # POOL STATUS
    # =====================================================

    def stats(self):

        with self.lock:

            return {

                "reserve_a":
                self.reserve_a,

                "reserve_b":
                self.reserve_b,

                "price":
                self.get_price(),

                "liquidity_providers":
                len(self.liquidity),

                "total_shares":
                self.total_shares,

                "fees_a":
                self.fees_a,

                "fees_b":
                self.fees_b
            }


# =========================================================
# GLOBAL EXAMPLE POOL
# =========================================================

pool = LiquidityPool()
