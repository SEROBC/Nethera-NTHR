def mine(block, difficulty):
    block.nonce = 0
    while not block.hash().startswith('0' * difficulty):
        block.nonce += 1
    return block.nonce
