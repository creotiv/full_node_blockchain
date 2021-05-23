import rsa
import binascii


class Address:
    def __init__(self, addr):
        if isinstance(addr, rsa.PublicKey):
            self.addr = addr
        else:
            if isinstance(addr,str):
                addr = addr.encode()
            # thats not clean bu i didnt find simple crypto library for 512 sha key
            # to get address/public_key short. 
            self.addr = rsa.PublicKey.load_pkcs1(b'-----BEGIN RSA PUBLIC KEY-----\n%b\n-----END RSA PUBLIC KEY-----\n' % addr)

    def __str__(self):
        return b''.join(self.addr.save_pkcs1().split(b'\n')[1:-2]).decode()

    @property
    def key(self):
        return self.addr

class Wallet:
    '''For real case wallet use ECDSA cryptography'''

    __slots__ = '_pub', '_priv'
    
    def __init__(self, pub=None, priv=None):
        if pub:
            self._pub = Address(pub)
            self._priv = rsa.PrivateKey.load_pkcs1(priv)

    @classmethod
    def create(cls):
        inst = cls(b'',b'')
        _pub, _priv = rsa.newkeys(512)
        inst._pub = Address(_pub)
        inst._priv = _priv
        return inst

    @classmethod
    def verify(cls, data, signature, address):
        signature = binascii.unhexlify(signature.encode())
        if not isinstance(address, Address):
            address = Address(address)
        try:
            return rsa.verify(data, signature, address.key) == 'SHA-256'
        except:
            return False 
    
    @property
    def address(self):
        return str(self._pub)

    @property
    def priv(self):
        return self._priv.save_pkcs1()

    def sign(self, hash):
        return binascii.hexlify(rsa.sign(hash, self._priv, 'SHA-256')).decode()