"""
Test script to verify telegram message formatting for scheduled time
"""
from datetime import datetime, timezone


def _format_schedule(dt: datetime) -> str:
    """Format datetime in a human-readable way for Telegram messages"""
    try:
        local_dt = dt.astimezone() if dt.tzinfo else dt
        months = [
            "yanvar",
            "fevral",
            "mart",
            "aprel",
            "may",
            "iyun",
            "iyul",
            "avgust",
            "sentabr",
            "oktabr",
            "noyabr",
            "dekabr",
        ]
        month_name = months[local_dt.month - 1] if 1 <= local_dt.month <= 12 else local_dt.strftime("%b")
        return f"{local_dt.day:02d}-{month_name} {local_dt.year} • {local_dt:%H:%M}"
    except Exception:
        # Fallback to a simple readable format if conversion fails
        try:
            return f"{dt.day:02d}.{dt.month:02d}.{dt.year} • {dt.hour:02d}:{dt.minute:02d}"
        except Exception:
            return str(dt)


# Test cases
if __name__ == "__main__":
    # Test 1: Current date and time
    test_dt1 = datetime(2025, 12, 25, 14, 30, 0, tzinfo=timezone.utc)
    print(f"Test 1 (December 25, 2025, 14:30): {_format_schedule(test_dt1)}")
    
    # Test 2: Different month
    test_dt2 = datetime(2025, 6, 15, 9, 45, 0, tzinfo=timezone.utc)
    print(f"Test 2 (June 15, 2025, 09:45): {_format_schedule(test_dt2)}")
    
    # Test 3: Datetime without timezone info
    test_dt3 = datetime(2025, 3, 10, 18, 0, 0)
    print(f"Test 3 (March 10, 2025, 18:00, no tz): {_format_schedule(test_dt3)}")
    
    # Test 4: Edge case - January 1st
    test_dt4 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    print(f"Test 4 (January 1, 2026, 00:00): {_format_schedule(test_dt4)}")
    
    # Test 5: Fallback format (simulating date/time strings)
    date_str = "25.12.2025"
    time_start = "14:30"
    time_end = "16:00"
    fallback_format = f"{date_str} • {time_start}-{time_end}"
    print(f"\nFallback format (when scheduled_datetime is None): {fallback_format}")
    
    print("\n✅ All tests completed!")
    print("\nExpected Telegram message format:")
    print("⏰ *Reja vaqt:*")
    print(f"{_format_schedule(test_dt1)}")
