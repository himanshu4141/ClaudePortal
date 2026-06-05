class Label:
    def __init__(
        self,
        font,
        text: str = "",
        color: int = 0xFFFFFF,
        x: int = 0,
        y: int = 0,
        anchor_point: tuple[float, float] | None = None,
        anchored_position: tuple[int, int] | None = None,
    ):
        self.font = font
        self._text = text
        self.color = color
        self.hidden = False
        self.anchor_point = anchor_point
        # anchored_position with anchor_point=(1.0, 0.5) means "right edge,
        # vertical center at this point". Convert to approximate x/y so the
        # renderer (which expects baseline-ish y) lands near the right spot.
        if anchored_position is not None:
            ax, ay = anchor_point or (0.0, 0.0)
            text_w = len(text) * getattr(font, "width", 6)
            text_h = getattr(font, "height", 8)
            self.x = anchored_position[0] - int(ax * text_w)
            self.y = anchored_position[1] + text_h // 2 - int(ay * text_h)
        else:
            self.x = x
            self.y = y

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value if value is not None else ""
