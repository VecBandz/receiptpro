import os
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Border, Side
from openpyxl.utils import get_column_letter


def write_to_excel_headless(save_path: str, receipts_data: list):
    """Write receipts data to an Excel file at save_path.

    receipts_data: list of (filename, extracted_text, parsed_dict) tuples.
    Returns save_path on success.
    """
    headers = ["Filename", "Company", "Date", "Items", "Amount", "Payment Method", "Extracted Text"]

    if not os.path.exists(save_path):
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        wb.save(save_path)

    wb = load_workbook(save_path)
    ws = wb.active

    bold_font = Font(bold=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Always rewrite headers
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = bold_font
        cell.border = thin_border

    # Write rows
    for filename, text, parsed in receipts_data:
        row = [filename, parsed["Company"], parsed["Date"], parsed["Items"],
               parsed["Amount"], parsed["Payment Method"], text]
        ws.append(row)

        for col in range(1, len(headers) + 1):
            ws.cell(row=ws.max_row, column=col).border = thin_border

    # Add totals row
    amount_col = headers.index("Amount") + 1
    total_row = ws.max_row + 1

    ws.cell(row=total_row, column=1, value="TOTAL").font = bold_font
    ws.cell(row=total_row, column=amount_col,
            value=f"=SUM({get_column_letter(amount_col)}2:{get_column_letter(amount_col)}{ws.max_row})").font = bold_font

    # Auto-size columns
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max_length + 2

    wb.save(save_path)
    return save_path
