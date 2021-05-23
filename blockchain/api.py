from .blocks import Tx, Block

class API:

    """
        Some wrapper around blockchain to add some logic without changing
        main blockchain code
    """

    def __init__(self, blockcain):
        self.bc = blockcain

    def get_user_balance(self, address):
        total = 0
        for v in self.bc.db.unspent_outputs_amount[str(address)].values():
            total += v
        return total

    def get_user_unspent_txs(self, address):
        res = []
        for tx_hash,out_hash in self.bc.db.unspent_txs_by_user_hash[str(address)]:
            amount = self.bc.db.unspent_outputs_amount[str(address)][out_hash]
            for index,out in enumerate(self.bc.db.transaction_by_hash[tx_hash]['outputs']):
                if out['hash'] == out_hash:
                    res.append({
                        "tx": tx_hash,
                        "output_index": index,
                        "out_hash": out_hash,
                        "amount": amount
                    })
        return res

    def get_chain(self, from_block:int, limit:int=20):
        res = [b.as_dict for b in self.bc.chain[from_block:from_block+limit]]
        # adding blocks from splitbrain
        if len(res) < limit:
            res += self.bc.fork_blocks.values()
        return res

    def add_block(self, block):
        block = Block.from_dict(block)
        res = self.bc.add_block(block)
        if res:
            self.bc.rollover_block(block)
        return res

    def mine_block(self, check_stop=None):
        self.bc.force_block(check_stop)

    def add_tx(self, tx):
        return self.bc.add_tx(Tx.from_dict(tx))

    def get_head(self):
        if not self.bc.head:
            return {}
        return self.bc.head.as_dict
            