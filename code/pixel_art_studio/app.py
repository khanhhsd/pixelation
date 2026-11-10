"""Desktop application entry point."""

import tkinter as tk

from pixel_art_studio.controller import PixelArtStudio


def main() -> None:
    root = tk.Tk()
    PixelArtStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
