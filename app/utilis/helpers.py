from datetime import datetime

def format_date(date_string):
    """Format date for display"""
    if isinstance(date_string, str):
        date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    else:
        date_obj = date_string
    return date_obj.strftime('%b %d, %Y')

def format_number(number):
    """Format large numbers with commas"""
    return f"{number:,}"

def truncate_text(text, length=50):
    """Truncate text to specified length"""
    if len(text) <= length:
        return text
    return text[:length] + '...'