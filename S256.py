from FieldElement import FieldElement
from Point import Point

from helper import encode_base58_checksum, hash160
#import hmac
#from io import BytesIO
#from random import randint

# Secp256k1の曲線のパラメータ
A = 0
B = 7
# 有限体の位数
P = 2**256 - 2**32 - 977
# 有限巡回群の位数
N = 0xfffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141

class S256Field(FieldElement):
    
    def __init__(self, num, prime=None):
        super().__init__(num=num, prime=P)

    def __repr__(self):
        return '{:x}'.format(self.num).zfill(64)

    def sqrt(self):
        return self**((P + 1 ) /4)

class S256Point(Point):
    
    def __init__(self, x, y, a=None, b=None):
        a, b = S256Field(A), S256Field(B)
        if type(x) == int:
            super().__init__(x=S256Field(x), y=S256Field(y), a=a, b=b)
        else:
            super().__init__(x=x, y=y, a=a, b=b)

    def __repr__(self):
        if self.x is None:
            return 'S256Point(infinity)'
        else:
            return f'S256Point({self.x}, {self.y})'

    def __rmul__(self, coefficient):
        coef = coefficient % N
        return super().__rmul__(coef)

    def verify(self, z, sig):
        """ 署名の検証
        PrivateKeyで署名をして，公開点で署名の検証を行う
        zは署名ハッシュ，つまりトランザクションをハッシュ化したもの
        sigはSignatureオブジェクトでrとsを持つ
        totalとsig,rが一致すれば署名が有効と判定
        """
        s_inv = pow(sig.s, N - 2, N)
        # u = z / s
        u = z * s_inv % N
        # v = r / s
        v = sig.r * s_inv % N
        total = u * G + v * self
        return total.x.num == sig.r

    def sec(self, compressed=True):
        ''' 公開鍵のシリアライズ
        バイトコードでシリアライズされた公開鍵を返す
        '''
        if compressed:
            if self.y.num % 2 == 0:
                return b'\x02' + self.x.num.to_bytes(32, 'big')
            else:
                return b'\x03' + self.x.num.to_bytes(32, 'big')
        else:
            return b'\x04' + self.x.num.to_bytes(32, 'big') + \
                self.y.num.to_bytes(32, 'big')

    def hash160(self, compressed=True):
        return hash160(self.sec(compressed))

    def address(self, compressed=True, testnet=False):
        '''Returns the address string'''
        h160 = self.hash160(compressed)
        if testnet:
            prefix = b'\x6f'
        else:
            prefix = b'\x00'
        return encode_base58_checksum(prefix + h160)

    @classmethod
    def parse(self, sec_bin):
        '''
        シリアライズされた公開鍵を入手したときにyを計算し，
        S256Pointオブジェクトを返す
        '''
        if sec_bin[0] == 4:  # <1>
            x = int.from_bytes(sec_bin[1:33], 'big')
            y = int.from_bytes(sec_bin[33:65], 'big')
            return S256Point(x=x, y=y)
        is_even = sec_bin[0] == 2  # <2>
        x = S256Field(int.from_bytes(sec_bin[1:], 'big'))
        # right side of the equation y^2 = x^3 + 7
        alpha = x**3 + S256Field(B)
        # solve for left side
        beta = alpha.sqrt()  # <3>
        if beta.num % 2 == 0:  # <4>
            even_beta = beta
            odd_beta = S256Field(P - beta.num)
        else:
            even_beta = S256Field(P - beta.num)
            odd_beta = beta
        if is_even:
            return S256Point(x, even_beta)
        else:
            return S256Point(x, odd_beta)
        

G = S256Point(
    0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
    0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8)

if __name__ == '__main__':
    pass