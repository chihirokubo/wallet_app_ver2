from .FieldElement import FieldElement


class Point(object):
    """ 楕円曲線上の点 
    楕円曲線y^2 = x^3 + ax + b上の点を表現
    """
    def __init__(self, x, y, a, b):
        self.a = a
        self.b = b
        self.x = x
        self.y = y
        # 無限遠点
        if self.x is None and self.y is None:
            return
        # 曲線上に存在するかの確認
        if y**2 != x**3 + a*x + b:
            error = f'({x},{y}) is not on the curve'
            raise ValueError(error)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y \
            and self.a == other.a and self.b == other.b

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        # 無限遠点
        if self.x is None:
            return 'Point(infinity)'
        # 有限退上の楕円曲線上の点
        elif isinstance(self.x, FieldElement):
            return f'Point({self.x.num},{self.y.num})_{self.a}_{self.b} F_{self.x.prime}'
        # 実数上の楕円曲線上の点
        else:
            return f'Point({self.x},{self.y})_{self.a}_{self.b}'

    def __add__(self, other):
        """ 楕円曲線上の点同士の加算 
        メモ：
            実数上でも有限体上でも加算は成立する
            どちらも体の性質を有しているため
        """
        # 異なる楕円曲線上の点同士は加算できない
        if self.a != other.a or self.b != other.b:
            raise TypeError(f'Points {self}, {other} are not on the same curve')

        # 無限遠点は点加算の加法単位元
        if self.x is None:
            return other
        if self.y is None:
            return self

        # x軸に垂直な直線上に2点が存在
        # 加算した結果は無限遠点
        if self.x == other.x and self.y != other.y:
            return self.__class__(None, None, self.a, self.y)
        
        # 直線が楕円曲線と3点で交わる
        # Formula (x3,y3)==(x1,y1)+(x2,y2)
        # s=(y2-y1)/(x2-x1)
        # x3=s**2-x1-x2
        # y3=s*(x1-x3)-y1
        if self.x != other.x:
            s = (other.y - self.y) / (other.x - self.x)
            x = s**2 - self.x - other.x
            y = s * (self.x - x) - self.y
            return self.__class__(x, y, self.a, self.b)

        # 直線と楕円曲線が1点で接する
        if self == other and self.y == 0 * self.x:
            return self.__class__(None, None, self.a, self.b) 

        # 直線は楕円曲線の接線で，接線が楕円曲線と1度交わる
        # Formula (x3,y3)=(x1,y1)+(x1,y1)
        # s=(3*x1**2+a)/(2*y1)
        # x3=s**2-2*x1
        # y3=s*(x1-x3)-y1
        if self == other:
            s = (3 * self.x**2 + self.a) / (2 * self.y)
            x = s**2 - 2 * self.x
            y = s * (self.x - x) - self.y
            return self.__class__(x, y, self.a, self.b)

    # スカラー倍
    def __rmul__(self, coefficient):
        coef = coefficient
        current = self
        result = self.__class__(None, None, self.a, self.b)
        while coef:
            if coef & 1:
                result += current
            current += current
            coef >>= 1
        return result


if __name__ == '__main__':
    print(Point(None, None, 0, 7))
        