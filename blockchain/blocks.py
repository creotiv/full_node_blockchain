import time
from hashlib import sha256
from merkletools import MerkleTools

from .wallet import Address


class Input:
    __slots__ = 'prev_tx_hash', 'output_index', 'signature', '_hash', 'address', 'index', 'amount'

    def __init__(self, prev_tx_hash, output_index, address, index=0):
        self.prev_tx_hash = prev_tx_hash
        self.output_index = output_index
        self.address = address
        self.index = 0
        self._hash = None
        self.signature = None
        self.amount = None

    def sign(self, wallet):
        hash_string = '{}{}{}{}'.format(
            self.prev_tx_hash, self.output_index, self.address, self.index
        ).encode()
        self.signature = wallet.sign(hash_string)

    @property
    def hash(self):
        if self._hash:
            return self._hash
        if not self.signature and self.prev_tx_hash != 'COINBASE':
            raise Exception('Sing the input first')
        hash_string = '{}{}{}{}'.format(
            self.prev_tx_hash, self.output_index, self.address, self.signature, self.index
        )
        self._hash = sha256(sha256(hash_string.encode()).hexdigest().encode('utf8')).hexdigest()
        return self._hash

    @property
    def as_dict(self):
        return {
            "prev_tx_hash":self.prev_tx_hash,
            "output_index":self.output_index,
            "address":str(self.address),
            "index":self.index,
            "hash":self.hash,
            "signature":self.signature
        }

    @classmethod
    def from_dict(cls, data):
        inst = cls(
            data['prev_tx_hash'],
            data['output_index'],
            Address(data['address']),
            data['index'],
        )
        inst.signature = data['signature']
        inst._hash = None
        return inst
        

class Output:
    __slots__ = '_hash', 'address', 'index', 'amount', 'input_hash'

    def __init__(self, address, amount, index=0):
        self.address = address
        self.index = 0
        self.amount = int(amount)
        # i use input hash here to make output hash unique, especialy for COINBASE tx
        self.input_hash = None
        self._hash = None

    @property
    def hash(self):
        if self._hash:
            return self._hash
   
        hash_string = '{}{}{}{}'.format(
            self.amount, self.index, self.address, self.input_hash
        )
        self._hash = sha256(sha256(hash_string.encode()).hexdigest().encode('utf8')).hexdigest()
        return self._hash

    @property
    def as_dict(self):
        return {
            "amount":int(self.amount),
            "address":str(self.address),
            "index":self.index,
            "input_hash": self.input_hash,
            "hash":self.hash
        }
        
    @classmethod
    def from_dict(cls, data):
        inst = cls(
            Address(data['address']),
            data['amount'],
            data['index'],
        )
        inst.input_hash = data['input_hash']
        inst._hash = None
        return inst

class Tx:
    __slots__ = 'inputs', 'outputs', 'timestamp', '_hash'

    def __init__(self, inputs, outputs, timestamp=None):   
        self.inputs = inputs
        self.outputs = outputs
        self.timestamp = timestamp or int(time.time())
        self._hash = None

    @property
    def hash(self):
        if self._hash:
            return self._hash

        # calculating input_hash for outputs
        inp_hash = sha256((str([el.as_dict for el in self.inputs]) + str(self.timestamp)).encode()).hexdigest()
        for el in self.outputs:
            el.input_hash = inp_hash

        hash_string = '{}{}{}'.format(
            [el.as_dict for el in self.inputs], [el.as_dict for el in self.outputs], self.timestamp
        )
        self._hash = sha256(sha256(hash_string.encode()).hexdigest().encode('utf8')).hexdigest()
        return self._hash

    @property
    def as_dict(self):
        inp_hash = sha256((str([el.as_dict for el in self.inputs]) + str(self.timestamp)).encode()).hexdigest()
        for el in self.outputs:
            el.input_hash = inp_hash
        return {
            "inputs":[el.as_dict for el in self.inputs],
            "outputs":[el.as_dict for el in self.outputs],
            "timestamp":self.timestamp,
            "hash":self.hash
        }

    @classmethod
    def from_dict(cls, data):
        inps = [Input.from_dict(el) for el in data['inputs']]
        outs = [Output.from_dict(el) for el in data['outputs']]
        inp_hash = sha256((str([el.as_dict for el in inps]) + str(data['timestamp'])).encode()).hexdigest()
        for el in outs:
            el.input_hash = inp_hash
            
        inst = cls(
            inps,
            outs,
            data['timestamp'],
        )
        inst._hash = None
        return inst


class Block:

    __slots__ = 'nonce', 'prev_hash', 'index', 'txs', 'timestamp', 'merkel_root'

    def __init__(self, txs, index, prev_hash, timestamp=None, nonce=0):
        self.txs = txs or []
        self.prev_hash = prev_hash
        self.index = index
        self.nonce = nonce
        self.timestamp = timestamp or int(time.time())
        self.merkel_root = None

    def build_merkel_tree(self):
        """
        Merkel Tree used to hash all the transactions, and on mining do not recompute Txs hash everytime
        Which making things much faster. 
        And tree used because we can append new Txs and rebuild root hash much faster, when just building 
        block before mine it.
        """
        if self.merkel_root:
            return self.merkel_root
        mt = MerkleTools(hash_type="SHA256")
        for el in self.txs:
            mt.add_leaf(el.hash)
        mt.make_tree()
        self.merkel_root = mt.get_merkle_root()
        return self.merkel_root

    def hash(self, nonce=None):
        if nonce:
            self.nonce = nonce
        block_string = '{}{}{}{}{}'.format(
            self.build_merkel_tree(), self.prev_hash, self.index, self.nonce, self.timestamp
        )
        return sha256(sha256(block_string.encode()).hexdigest().encode('utf8')).hexdigest()

    @property
    def as_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "hash": self.hash(),
            "txs": [el.as_dict for el in self.txs],
            "nonce": self.nonce,
            "merkel_root":self.merkel_root
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            [Tx.from_dict(el) for el in data['txs']],
            data['index'],
            data['prev_hash'],
            data['timestamp'],
            data['nonce']
        )