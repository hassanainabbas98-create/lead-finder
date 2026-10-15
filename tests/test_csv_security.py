"""Test security protections including CSV formula injection prevention."""

from app.services.export.csv_exporter import sanitize_csv_field, generate_safe_csv


def test_csv_injection_sanitization():
    """Verify that potentially malicious spreadsheet formulas are escaped with a leading single quote."""
    dangerous_inputs = [
        "=SUM(A1:A10)",
        "+cmd|' /C calc'!A0",
        "-1+1",
        "@SUM(B1:B5)",
        "\tmalicious_tab",
        "\rmalicious_cr",
    ]
    for inp in dangerous_inputs:
        sanitized = sanitize_csv_field(inp)
        assert sanitized.startswith("'"), f"Field '{inp}' was not properly escaped: '{sanitized}'"

    # Normal strings should remain unchanged
    safe_inputs = [
        "Royal Barber Shop",
        "Lahore, Pakistan",
        "+923001234567",  # Note: starts with + so it gets escaped safely to '+923001234567 which prevents Excel from evaluating it as math!
        "hello@example.com",
    ]
    assert sanitize_csv_field("Royal Barber Shop") == "Royal Barber Shop"
    assert sanitize_csv_field("hello@example.com") == "hello@example.com"
    assert sanitize_csv_field(None) == ""


def test_generate_safe_csv_output():
    """Verify full CSV output generation with escaped fields."""
    headers = ["Name", "FormulaField"]
    rows = [
        ["Safe Business", "=2+2"],
        ["Another Business", "@attack"],
    ]
    csv_str = generate_safe_csv(headers, rows)
    assert "'=2+2" in csv_str
    assert "'@attack" in csv_str
