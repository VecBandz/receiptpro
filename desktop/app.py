import sys
import os

if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    if sys.platform == "win32":
        os.environ["TESSERACT_CMD"] = os.path.join(base, "tesseract", "tesseract.exe")
    os.environ["POPPLER_PATH"] = os.path.join(base, "poppler")

from desktop.gui import ReceiptProApp

if __name__ == "__main__":
    ReceiptProApp().run()
