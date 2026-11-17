import re

COMPANY_SKIP = [
    re.compile(r'receipt\s*(id|no|#)', re.I),
    re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'),
    re.compile(r'^\d+\s+\w+.*(ave|st|rd|blvd|dr|ln)', re.I),
    re.compile(r'^(tel|phone|fax|www\.|\d{3}[-.\s]\d{3})', re.I),
    re.compile(r'^\s*$'),
]


AMOUNT_RE = re.compile(r'(\$?[\d,]+\.\d{2})')

# Labels in order of preference. The final total wins over a subtotal, even
# when the subtotal appears first on the receipt.
AMOUNT_LABELS = [
    re.compile(r'\bgrand\s+total\b', re.I),
    re.compile(r'\b(amount|balance)\s+due\b', re.I),
    re.compile(r'(?<!sub)(?<!sub\s)\btotal\b', re.I),
    re.compile(r'\bsub\s?total\b', re.I),
]


def _find_amount(lines):
    """Return the receipt's final amount as a string like '41.51'."""
    for label in AMOUNT_LABELS:
        candidate = ""
        for line in lines:
            if not label.search(line):
                continue
            if label is not AMOUNT_LABELS[3] and re.search(r'\bsub\s?total\b|\btax\b', line, re.I):
                continue
            match = AMOUNT_RE.search(line[label.search(line).end():])
            if match:
                candidate = match.group(1)  # keep the last match for this label
        if candidate:
            return candidate.replace("$", "").replace(",", "")
    return ""


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

    for line in lines[:6]:
        if len(line.strip()) > 2 and not any(p.search(line) for p in COMPANY_SKIP):
            parsed["Company"] = line.strip()
            break

    date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    if date_match:
        parsed["Date"] = date_match.group(1)

    parsed["Amount"] = _find_amount(lines)

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
