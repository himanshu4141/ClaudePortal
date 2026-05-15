"""Tk window that shows the emulated 64x32 panel scaled up."""
from __future__ import annotations

import tkinter as tk
from PIL import Image, ImageTk


class Viewer:
    def __init__(self, scale: int = 10, width: int = 64, height: int = 32, title: str = "ClaudePortal Emulator"):
        self.scale = scale
        self.width = width
        self.height = height
        self._alive = True

        self.root = tk.Tk()
        self.root.title(title)
        self.root.resizable(False, False)
        self.canvas = tk.Canvas(
            self.root,
            width=width * scale,
            height=height * scale,
            bg="black",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self._image_id: int | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self) -> None:
        self._alive = False
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def update_image(self, pil_image: Image.Image) -> None:
        if not self._alive:
            return
        scaled = pil_image.resize(
            (self.width * self.scale, self.height * self.scale),
            Image.NEAREST,
        )
        self._photo = ImageTk.PhotoImage(scaled)
        if self._image_id is None:
            self._image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)
        else:
            self.canvas.itemconfig(self._image_id, image=self._photo)

    def poll(self) -> None:
        if not self._alive:
            return
        try:
            self.root.update_idletasks()
            self.root.update()
        except tk.TclError:
            self._alive = False

    def alive(self) -> bool:
        return self._alive
