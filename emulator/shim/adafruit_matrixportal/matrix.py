class _Display:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.root_group = None


class Matrix:
    def __init__(self, width: int = 64, height: int = 32, bit_depth: int = 4):
        self.display = _Display(width, height)
