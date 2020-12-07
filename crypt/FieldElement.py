

class FieldElement(object):
    """ 有限体の要素 """
    def __init__(self, num, prime):
        if num<0 or num>=prime:
            error = f'{num} not in field range to {prime-1}'
            raise ValueError(error)
        self.num = num     # 有限体の要素
        self.prime = prime # 有限体の位数(性質上素数を選択)

    def __repr__(self):
        return f'F_{self.prime}({self.num})'

    def __eq__(self, other):
        if other is None:
            return False
        return self.num == other.num and self.prime == other.prime

    def __ne__(self, other):
        return not (self == other)

    """ 演算子をモジュロ演算でオーバーロード 

    self.primeを法としたmod演算を定義

    """

    # +
    def __add__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot add two numbers in different Fields')
        num = (self.num + other.num) % self.prime
        return self.__class__(num, self.prime)

    # -
    def __sub__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot subtract two numbers in different Fields')
        num = (self.num - other.num) % self.prime
        return self.__class__(num, self.prime)

    # *
    def __mul__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot multiply two numbers in different Fields')
        num = (self.num * other.num) % self.prime
        return self.__class__(num, self.prime)
    
    # **
    def __pow__(self, exponent):
        n = exponent % (self.prime - 1)
        num = pow(self.num, n, self.prime)
        return self.__class__(num, self.prime)

    # /
    def __truediv__(self, other):
        if self.prime != other.prime:
            raise TypeError('Cannot add divide numbers in different Fields')
        num = (self.num * pow(other.num, self.prime- 2, self.prime)) % self.prime
        return self.__class__(num, self.prime)

    # 係数をかけた時
    def __rmul__(self, coefficient):
        num = (self.num * coefficient) % self.prime
        return self.__class__(num, self.prime)

if __name__ == '__main__':
    pass

    
        