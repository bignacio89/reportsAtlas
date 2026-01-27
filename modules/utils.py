import base64

def currency_format(value):
    """Standard currency formatter used across all reports"""
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return "0.00"

def get_base64_logo(file_path):
    """Converts image to string for HTML embedding"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except FileNotFoundError:
        return ""
