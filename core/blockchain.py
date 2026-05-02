from core.block import Block
from consensus.pow import mine

class Blockchain:
    def __init__(self):
        self.chain = []
        self.pending = []
        self.difficulty = 4
        self.create_genesis()

    def create_genesis(self):
        genesis = Block(0, "0", [])
        self.chain.append(genesis)

    def last_block(self):
        return self.chain[-1]

    def add_tx(self, tx):
        self.pending.append(tx)

    def mine_block(self):
        block = Block(
            len(self.chain),
            self.last_block().hash(),
            self.pending
        )

        mine(block, self.difficulty)

        self.chain.append(block)
        self.pending = []
