import re
from datetime import datetime, timedelta

def parse_natural_date(text: str):
    """
    Detects date keywords in text and returns (cleaned_text, iso_date).
    Supported keywords: today, tomorrow, next <weekday>
    """
    now = datetime.now()
    keywords = {
        "today": now,
        "tomorrow": now + timedelta(days=1),
    }

    # Weekdays for "next <weekday>"
    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }

    cleaned_text = text
    iso_date = None

    # Check for today/tomorrow
    for word, target_date in keywords.items():
        pattern = rf"\b{word}\b"
        if re.search(pattern, text, re.IGNORECASE):
            iso_date = target_date.strftime("%Y-%m-%d")
            cleaned_text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
            return cleaned_text, iso_date

    # Check for "next <weekday>"
    match = re.search(r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", text, re.IGNORECASE)
    if match:
        day_name = match.group(1).lower()
        target_weekday = weekdays[day_name]
        current_weekday = now.weekday()
        
        days_ahead = target_weekday - current_weekday
        if days_ahead <= 0: # Target day is in the next week
            days_ahead += 7
            
        target_date = now + timedelta(days=days_ahead)
        iso_date = target_date.strftime("%Y-%m-%d")
        cleaned_text = re.sub(match.group(0), "", text, flags=re.IGNORECASE).strip()
        return cleaned_text, iso_date

    return cleaned_text, iso_date
