# =========================================================
# Nethera-NTHR
# defi/router.py
# Multi-Pool Swap Router (Uniswap V2 style)
# =========================================================

import threading

class Router:

    def __init__(self):

        self.pools = {}

        self.lock = threading.Lock()

    # -----------------------------------------------------
    # Register pool
    # -----------------------------------------------------

    def register_pool(self, name, pool):

        with self.lock:
            self.pools[name] = pool

    # -----------------------------------------------------
    # Find best price pool
    # -----------------------------------------------------

    def best_pool(self):

        best = None
        best_price = 0

        with self.lock:

            for name, pool in self.pools.items():

                price = pool.get_price()

                if price > best_price:

                    best_price = price
                    best = pool

        return best

    # -----------------------------------------------------
    # Multi-hop swap (A -> B across pools)
    # -----------------------------------------------------

    def swap(self, amount_in, path):

        amount = amount_in

        for i in range(len(path) - 1):

            pool = self.pools.get(
                f"{path[i]}_{path[i+1]}"
            )

            if not pool:
                return None

            if path[i] == "NTHR":

                amount = pool.swap_a_to_b(amount)

            else:

                amount = pool.swap_b_to_a(amount)

        return amount
