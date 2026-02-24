import os
import glob
import platform
import subprocess
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

from core.ml_parser import parse_receipt_ml
from core.exporter import write_to_excel_headless


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ReceiptProApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Receipt Pro")
        self.root.geometry("900x700")
        self._build_ui()

    def _build_ui(self):
        top_frame = ctk.CTkFrame(self.root, corner_radius=10)
        top_frame.pack(fill="x", padx=10, pady=10)

        main_frame = ctk.CTkFrame(self.root, corner_radius=10)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.text_area = ScrolledText(main_frame, wrap="word", font=("Consolas", 12), height=20)
        self.text_area.pack(fill="both", expand=True, padx=10, pady=10)

        self.progress = ctk.CTkProgressBar(main_frame)
        self.progress.pack(fill="x", padx=10, pady=5)
        self.progress.set(0)

        ctk.CTkButton(top_frame, text="Open Files", command=self._open_file).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(top_frame, text="Process All Receipts", command=self._process_all_receipts).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(top_frame, text="Show Info", command=self._show_info).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(top_frame, text="Clear Text", command=self._clear_text).pack(side="left", padx=5, pady=5)

    def _open_file(self):
        filepaths = filedialog.askopenfilenames(
            title="Select receipt files",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tiff"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*"),
            ]
        )
        if not filepaths:
            messagebox.showinfo("Cancelled", "No files selected.")
            return
        threading.Thread(target=self._process_receipts, args=(list(filepaths),), daemon=True).start()

    def _process_all_receipts(self):
        receipts_dir = os.path.expanduser("~/receipts")
        if not os.path.exists(receipts_dir):
            messagebox.showerror("Error", f"Directory not found:\n{receipts_dir}")
            return
        patterns = ["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp", "*.tiff", "*.pdf"]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(os.path.join(receipts_dir, pattern)))
        if not files:
            messagebox.showinfo("No Receipts", "No receipt files found in ~/receipts/")
            return
        threading.Thread(target=self._process_receipts, args=(files,), daemon=True).start()

    def _show_info(self):
        messagebox.showinfo("Information", "This app extracts text from receipts, parses key information, and saves it to Excel.")

    def _clear_text(self):
        self.text_area.delete("1.0", "end")

    def _process_receipts(self, filepaths):
        receipts_data = []
        self._log(f"Processing {len(filepaths)} receipts...\n\n")
        self._set_progress(0)

        for i, fp in enumerate(filepaths):
            try:
                parsed, extracted = parse_receipt_ml(fp)
                receipts_data.append((os.path.basename(fp), extracted, parsed))
            except Exception as e:
                self._log(f"\u2717 {os.path.basename(fp)}: {e}\n")
            self._set_progress((i + 1) / len(filepaths))

        excel_path = self._write_to_excel_gui(filepaths, receipts_data)
        if excel_path:
            self._log(f"Saved results to: {excel_path}\n")
            self._log("Opening Excel file...\n\n")
            self._open_excel_file(excel_path)

    def _write_to_excel_gui(self, filepaths, receipts_data):
        receipts_dir = os.path.dirname(filepaths[0]) if filepaths else os.getcwd()
        save_path = filedialog.asksaveasfilename(
            title="Save Excel File As",
            defaultextension=".xlsx",
            initialdir=receipts_dir,
            initialfile="receipts.xlsx",
            filetypes=[("Excel Files", "*.xlsx")]
        )
        if not save_path:
            return None
        return write_to_excel_headless(save_path, receipts_data)

    def _open_excel_file(self, path):
        if not path:
            return
        system = platform.system()
        if system == "Linux":
            subprocess.Popen(["xdg-open", path])
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        elif system == "Windows":
            os.startfile(path)

    def _log(self, msg):
        self.text_area.insert("end", msg)
        self.text_area.see("end")
        self.root.update_idletasks()

    def _set_progress(self, val):
        self.progress.set(val)
        self.root.update_idletasks()

    def run(self):
        self.root.mainloop()
