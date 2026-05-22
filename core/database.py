# core/database.py

import sqlite3
import os
import threading


class BlockchainDB:

    def __init__(self, db_path="data/blockchain.db"):

        os.makedirs("data", exist_ok=True)

        self.db_path = db_path

        self.lock = threading.Lock()

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self.create_tables()

    # -----------------------------------
    # CREATE TABLES
    # -----------------------------------

    def create_tables(self):

        with self.lock:

            cursor = self.conn.cursor()

            # BLOCKS

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS blocks (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                block_index INTEGER UNIQUE,

                timestamp REAL,

                previous_hash TEXT,

                hash TEXT UNIQUE,

                nonce INTEGER

            )
            """)

            # TRANSACTIONS

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                block_index INTEGER,

                sender TEXT,

                receiver TEXT,

                amount REAL,

                fee REAL,

                timestamp REAL,

                tx_hash TEXT UNIQUE,

                signature TEXT,

                public_key TEXT

            )
            """)

            # MEMPOOL

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS mempool (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                sender TEXT,

                receiver TEXT,

                amount REAL,

                fee REAL,

                timestamp REAL,

                tx_hash TEXT UNIQUE,

                signature TEXT,

                public_key TEXT

            )
            """)

            # PEERS

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS peers (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                node TEXT UNIQUE

            )
            """)

            self.conn.commit()

    # -----------------------------------
    # SAVE BLOCK
    # -----------------------------------

    def save_block(self, block):

        with self.lock:

            cursor = self.conn.cursor()

            cursor.execute("""
            INSERT OR IGNORE INTO blocks (

                block_index,

                timestamp,

                previous_hash,

                hash,

                nonce

            )
            VALUES (?, ?, ?, ?, ?)
            """, (

                block["index"],

                block["timestamp"],

                block["previous_hash"],

                block["hash"],

                block["nonce"]

            ))

            for tx in block["transactions"]:

                cursor.execute("""
                INSERT OR IGNORE INTO transactions (

                    block_index,

                    sender,

                    receiver,

                    amount,

                    fee,

                    timestamp,

                    tx_hash,

                    signature,

                    public_key

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (

                    block["index"],

                    tx["sender"],

                    tx["receiver"],

                    tx["amount"],

                    tx.get("fee", 0),

                    tx["timestamp"],

                    tx.get("tx_hash"),

                    tx.get("signature"),

                    tx.get("public_key")

                ))

            self.conn.commit()

    # -----------------------------------
    # LOAD CHAIN
    # -----------------------------------

    def load_chain(self):

        with self.lock:

            cursor = self.conn.cursor()

            cursor.execute("""
            SELECT *
            FROM blocks
            ORDER BY block_index ASC
            """)

            blocks = cursor.fetchall()

            chain = []

            for block_row in blocks:

                block_index = block_row["block_index"]

                tx_cursor = self.conn.cursor()

                tx_cursor.execute("""
                SELECT *
                FROM transactions
                WHERE block_index = ?
                """, (block_index,))

                tx_rows = tx_cursor.fetchall()

                transactions = []

                for tx in tx_rows:

                    transactions.append({

                        "sender": tx["sender"],

                        "receiver": tx["receiver"],

                        "amount": tx["amount"],

                        "fee": tx["fee"],

                        "timestamp": tx["timestamp"],

                        "tx_hash": tx["tx_hash"],

                        "signature": tx["signature"],

                        "public_key": tx["public_key"]

                    })

                block = {

                    "index": block_row["block_index"],

                    "timestamp": block_row["timestamp"],

                    "previous_hash": block_row["previous_hash"],

                    "hash": block_row["hash"],

                    "nonce": block_row["nonce"],

                    "transactions": transactions

                }

                chain.append(block)

            return chain

    # -----------------------------------
    # SAVE MEMPOOL
    # -----------------------------------

    def save_mempool(self, mempool):

        with self.lock:

            cursor = self.conn.cursor()

            cursor.execute("DELETE FROM mempool")

            for tx in mempool:

                cursor.execute("""
                INSERT OR IGNORE INTO mempool (

                    sender,

                    receiver,

                    amount,

                    fee,

                    timestamp,

                    tx_hash,

                    signature,

                    public_key

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (

                    tx["sender"],

                    tx["receiver"],

                    tx["amount"],

                    tx.get("fee", 0),

                    tx["timestamp"],

                    tx.get("tx_hash"),

                    tx.get("signature"),

                    tx.get("public_key")

                ))

            self.conn.commit()

    # -----------------------------------
    # LOAD MEMPOOL
    # -----------------------------------

    def load_mempool(self):

        with self.lock:

            cursor = self.conn.cursor()

            cursor.execute("""
            SELECT *
            FROM mempool
            """)

            rows = cursor.fetchall()

            mempool = []

            for tx in rows:

                mempool.append({

                    "sender": tx["sender"],

                    "receiver": tx["receiver"],

                    "amount": tx["amount"],

                    "fee": tx["fee"],

                    "timestamp": tx["timestamp"],

                    "tx_hash": tx["tx_hash"],

                    "signature": tx["signature"],

                    "public_key": tx["public_key"]

                })

            return mempool

    # -----------------------------------
    # SAVE PEER
    # -----------------------------------

    def save_peer(self, peer):

        with self.lock:

            cursor = self.conn.cursor()

            cursor.execute("""
            INSERT OR IGNORE INTO peers (node)
            VALUES (?)
            """, (peer,))

            self.conn.commit()

    # -----------------------------------
    # LOAD PEERS
    # -----------------------------------

    def load_peers(self):

        with self.lock:

            cursor = self.conn.cursor()

            cursor.execute("""
            SELECT node
            FROM peers
            """)

            rows = cursor.fetchall()

            peers = []

            for row in rows:

                peers.append(row["node"])

            return peers

    # -----------------------------------
    # RESET DATABASE
    # -----------------------------------

    def reset_chain(self):

        with self.lock:

            cursor = self.conn.cursor()

            cursor.execute("DELETE FROM blocks")
            cursor.execute("DELETE FROM transactions")
            cursor.execute("DELETE FROM mempool")

            self.conn.commit()

    # -----------------------------------
    # CLOSE DATABASE
    # -----------------------------------

    def close(self):

        with self.lock:

            self.conn.close()
