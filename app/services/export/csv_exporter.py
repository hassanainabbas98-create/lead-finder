"""Safe CSV exporter with spreadsheet formula injection protection."""

import io
import csv
from typing import List, Dict, Any


def sanitize_csv_field(val: Any) -> str:
    """
    Sanitize field against spreadsheet formula injection (CSV Injection).
    If a string starts with =, +, -, @, \t, or \r, prefix with a single quote.
    """
    if val is None:
        return ""
    s = str(val)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


def generate_safe_csv(headers: List[str], rows: List[List[Any]]) -> str:
    """Generate a sanitized CSV string from headers and rows."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        sanitized_row = [sanitize_csv_field(col) for col in row]
        writer.writerow(sanitized_row)
    return output.getvalue()
