class Label:
    def __init__(self, font, text: str = "", color: int = 0xFFFFFF, x: int = 0, y: int = 0):
        self.font = font
        self._text = text
        self.color = color
        self.x = x
        self.y = y
        self.hidden = False

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value if value is not None else ""
