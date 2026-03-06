from datetime import datetime, timedelta
import re

def parse_date(date_str: str) -> str:
    """Parse date string like YYYY-MM-DD or MM-DD (assumes current year)"""
    if not date_str:
        return None
    
    # Check if already ISO
    if 'T' in date_str:
        return date_str
        
    try:
        if len(date_str) == 5 and '-' in date_str:  # MM-DD
            year = datetime.now().year
            date_obj = datetime.strptime(f"{year}-{date_str}", "%Y-%m-%d")
        else:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.replace(hour=23, minute=59, second=59).isoformat()
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or MM-DD")

def calculate_next_recurrence(current_due: str, recur_pattern: str) -> str:
    """Calculate the next due date based on a recurrence pattern"""
    if not current_due or not recur_pattern:
        return None
        
    current_date = datetime.fromisoformat(current_due)
    pattern = recur_pattern.lower()
    
    if pattern == "daily":
        next_date = current_date + timedelta(days=1)
    elif pattern == "weekly":
        next_date = current_date + timedelta(weeks=1)
    elif pattern == "monthly":
        # Rough approximation, +30 days
        next_date = current_date + timedelta(days=30)
    elif pattern == "yearly":
        # Rough approximation, +365 days
        next_date = current_date + timedelta(days=365)
    else:
        # Try to parse things like "2w", "3d"
        match = re.match(r"(\d+)([dwmy])", pattern)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit == 'd':
                next_date = current_date + timedelta(days=amount)
            elif unit == 'w':
                next_date = current_date + timedelta(weeks=amount)
            elif unit == 'm':
                next_date = current_date + timedelta(days=amount * 30)
            elif unit == 'y':
                next_date = current_date + timedelta(days=amount * 365)
            else:
                return None
        else:
            return None
            
    return next_date.isoformat()

def extract_tags(description: str) -> tuple[str, list[str]]:
    """Extract +tags from description and return clean description + tags list"""
    tags = []
    clean_parts = []
    
    for word in description.split():
        if word.startswith('+') and len(word) > 1:
            tags.append(word[1:])
        else:
            clean_parts.append(word)
            
    return " ".join(clean_parts), tags
