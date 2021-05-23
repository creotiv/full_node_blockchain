import pickle
from collections import defaultdict

class DB:
    """
    Class that just emulates some sort of DB used to save all data
    """
    def __init__(self):
        self.config = {
            'txs_per_block': 4,
            'mining_reward': 25,
            'difficulty': 22,
        }

        self.block_index = 0
        self.transaction_by_hash = {}
        self.unspent_txs_by_user_hash = defaultdict(set)
        self.unspent_outputs_amount = defaultdict(dict)

    '''
        Just simple routine to save/restore db data for block number
    '''
    def backup(self):
        with open('block_%s' % self.block_index,'wb') as fp:
            pickle.dump(self.__dict__, fp)

    @classmethod
    def restore(cls, block_index):
        with open('block_%s' % block_index, 'rb') as fp:
            data = pickle.load(fp)

        inst = cls()
        inst.__dict__ = data
        return inst