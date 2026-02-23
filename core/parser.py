import re


def parse_receipt(text):
    parsed = {
        "Company": "",
        "Date": "",
        "Items": "",
        "Amount": "",
        "Payment Method": "",
    }

    lower_text = text.lower()
    lines = text.splitlines()

    if lines:
        parsed["Company"] = lines[0].strip()

    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    if date_match:
        parsed["Date"] = date_match.group(1)

    amount_match = re.search(r'(total|subtotal|amount due|grand total)\s*[:$]*\s*(\$?[\d,]+\.\d{2})',
                             lower_text, re.IGNORECASE)
    if amount_match:
        parsed["Amount"] = amount_match.group(2)

    payment_keywords = ['visa', 'mastercard', 'amex', 'american express', 'discover',
                        'cash', 'check', 'debit', 'credit card', 'paypal']
    for keyword in payment_keywords:
        if keyword in lower_text:
            parsed["Payment Method"] = keyword.capitalize()
            break

    items = []
    capturing_items = False
    for line in lines:
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in ['item', 'description', 'qty', 'product']):
            capturing_items = True
            continue
        if capturing_items:
            if any(keyword in lower_line for keyword in ['subtotal', 'total', 'tax', 'payment']):
                break
            if re.search(r'\d+\.\d{2}', line):
                items.append(line.strip())

    if not items and lines:
        for line in lines[1:]:
            if 'total' in line.lower():
                break
            if re.search(r'\d+\.\d{2}', line):
                items.append(line.strip())

    parsed["Items"] = "; ".join(items) if items else ""
    return parsed
