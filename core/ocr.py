import os
import pytesseract
from PIL import Image, ImageOps, ImageFilter
from pdf2image import convert_from_path


def extract_text_from_file(filepath):
    cmd = os.environ.get("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd

    poppler_path = os.environ.get("POPPLER_PATH") or None
    ext = filepath.lower()

    try:
        if ext.endswith(".pdf"):
            pages = convert_from_path(filepath, poppler_path=poppler_path)
            text = ""
            for page in pages:
                page = page.convert("L")
                page = ImageOps.exif_transpose(page)
                page = page.filter(ImageFilter.SHARPEN)
                page = page.point(lambda x: 0 if x < 150 else 255)
                page_text = pytesseract.image_to_string(page, config="--oem 1 --psm 6")
                print("PDF OCR output:", repr(page_text[:200]))
                text += page_text + "\n"
            return text.strip()

        else:
            img = Image.open(filepath)
            img = ImageOps.exif_transpose(img)
            img = img.convert("L")
            img = img.filter(ImageFilter.SHARPEN)
            img = img.point(lambda x: 0 if x < 150 else 255)
            text = pytesseract.image_to_string(img, config="--oem 1 --psm 6")
            print("Image OCR Output:", repr(text[:200]))
            return text.strip()

    except Exception as e:
        print("OCR ERROR:", e)
        return f"[OCR ERROR] {e}"
