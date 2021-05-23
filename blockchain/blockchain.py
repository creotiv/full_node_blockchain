from .blocks import Block, Tx, Input, Output
from .verifiers import TxVerifier, BlockOutOfChain, BlockVerifier, BlockVerificationFailed
import logging

logger = logging.getLogger('Blockchain')


class Blockchain: 

    __slots__ =  'max_nonce', 'chain', 'unconfirmed_transactions', 'db', 'wallet', 'on_new_block', 'on_prev_block', 'current_block_transactions', 'fork_blocks'

    def __init__(self, db, wallet, on_new_block=None, on_prev_block=None):
        self.max_nonce = 2**32
    
        self.db = db
        self.wallet = wallet
        self.on_new_block = on_new_block
        self.on_prev_block = on_prev_block

        self.unconfirmed_transactions = set()
        self.current_block_transactions = set()
        self.chain = []
        self.fork_blocks = {}    
 
    def create_first_block(self):
        """
        Creating first block in a chain. Only COINBASE Tx.
        """
        tx = self.create_coinbase_tx()
        block = Block([tx], 0, 0x0)
        self.mine_block(block)

    def create_coinbase_tx(self, fee=0):
        inp = Input('COINBASE',0,self.wallet.address,0)
        inp.sign(self.wallet)
        out = Output(self.wallet.address, self.db.config['mining_reward']+fee, 0)
        return Tx([inp],[out])

    def is_valid_block(self, block):
        bv = BlockVerifier(self.db)
        return bv.verify(self.head, block)

    def add_block(self, block):
        if self.head and block.hash() == self.head.hash():
            logger.error('Duplicate block')
            return False
        try:
            self.is_valid_block(block)
        except BlockOutOfChain:
            # Here we covering split brain case only for next 2 leves of blocks
            # with high difficulty its a rare case, and more then 2 level much more rare.
            if block.prev_hash == self.head.prev_hash:
                logger.error('Split Brain detected')
                self.fork_blocks[block.hash()] = block
                return False
            else:
                for b_hash, b in self.fork_blocks.items():
                    if block.prev_hash == b_hash:
                        logger.error('Split Brain fixed. Longer chain choosen')
                        self.rollback_block()
                        self.chain.append(b)
                        self.chain.append(block)
                        self.fork_blocks = {}
                        return True
                    logger.error('Second Split Brain detected. Not programmed to fix this')
                    return False
        except BlockVerificationFailed as e:
            logger.error('Block verification failed: %s' % e)
            return False
        else:        
            self.chain.append(block)
            self.fork_blocks = {}
            logger.info('   Block added')
            return True
        logger.error('Hard chain out of sync')

    def add_tx(self, tx):
        if self.db.transaction_by_hash.get(tx.hash):
            return False
        tv = TxVerifier(self.db)
        fee = tv.verify(tx.inputs, tx.outputs)
        self.db.transaction_by_hash[tx.hash] = tx.as_dict
        self.unconfirmed_transactions.add((fee, tx.hash))
        return True
       
    def force_block(self, check_stop=None):
        '''
        Forcing to mine block. Gthering all txs with some limit. First take Txs with bigger fee.
        '''
        txs = sorted(self.unconfirmed_transactions, key=lambda x:-x[0])[:self.db.config['txs_per_block']]
        self.current_block_transactions = set(txs)
        fee = sum([v[0] for v in txs])
        txs = [Tx.from_dict(self.db.transaction_by_hash[v[1]]) for v in txs ]
        block = Block(
            txs=[self.create_coinbase_tx(fee)] + txs,
            index=self.head.index+1,
            prev_hash=self.head.hash(),
        )
        self.mine_block(block, check_stop)

    def rollover_block(self, block):
        '''
        As we use some sort of DB, we need way to update it depends we need add block or remove.
        So we have 2 methods Rollover and Rollback.
        Also i added some sort of callback in case some additional functionality should be added on top.
        For example some Blockchain analytic DB.
        '''
        self.unconfirmed_transactions -= self.current_block_transactions
        self.db.block_index = block.index
        for tx in block.txs:
            self.db.transaction_by_hash[tx.hash] = tx.as_dict
            for out in tx.outputs:
                self.db.unspent_txs_by_user_hash[str(out.address)].add((tx.hash,out.hash))
                self.db.unspent_outputs_amount[str(out.address)][out.hash] = int(out.amount)
            for inp in tx.inputs:
                if inp.prev_tx_hash == 'COINBASE':
                    continue
                prev_out = self.db.transaction_by_hash[inp.prev_tx_hash]['outputs'][inp.output_index]
                self.db.unspent_txs_by_user_hash[prev_out['address']].remove((inp.prev_tx_hash,prev_out['hash']))
                del self.db.unspent_outputs_amount[prev_out['address']][prev_out['hash']]
        if self.on_new_block:
            self.on_new_block(block, self.db)
        self.current_block_transactions = set()

    def rollback_block(self):
        block = self.chain.pop()
        self.db.block_index -= 1
        total_amount_in = 0
        total_amount_out = 0

        for tx in block.txs:
            # removing new unspent outputs
            for out in tx.outputs:
                self.db.unspent_txs_by_user_hash[str(out.address)].remove((tx.hash,out.hash))
                del self.db.unspent_outputs_amount[str(out.address)][out.hash]
                total_amount_out += out.amount
            # adding back previous unspent outputs
            for inp in tx.inputs:
                if inp.prev_tx_hash == 'COINBASE':
                    continue
                prev_out = self.db.transaction_by_hash[inp.prev_tx_hash]['outputs'][inp.output_index]
                self.db.unspent_txs_by_user_hash[prev_out['address']].add((inp.prev_tx_hash,prev_out['hash']))
                self.db.unspent_outputs_amount[prev_out['address']][prev_out['hash']] = prev_out['amount']      
                total_amount_in += int(prev_out['amount'])

            # adding Tx back un unprocessed stack
            fee = total_amount_in - total_amount_out
            self.unconfirmed_transactions.add((fee,tx.hash))

        
        if self.on_prev_block:
            self.on_prev_block(block, self.db)

    def mine_block(self, block, check_stop=None):
        '''
        Mine a block with ability to stop in case if check callback return True
        '''
        for n in range(self.max_nonce):
            if check_stop and check_stop():
                logger.error('Mining interrupted.')
                return
            if int(block.hash(nonce=n), 16) <= (2 ** (256-self.db.config['difficulty'])):
                self.add_block(block)
                self.rollover_block(block)
                logger.info('  Block mined at nonce: %s' % n)
                break



    @property
    def head(self):
        if not self.chain:
            return None
        return self.chain[-1]

    @property
    def blockchain(self):
        return [el.as_dict for el in reversed(self.chain)]

