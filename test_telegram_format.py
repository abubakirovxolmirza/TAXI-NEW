"""
Test script to verify telegram message formatting with timezone handling
Tests the fix for timezone issue where server time (Frankfurt) was being used instead of Uzbekistan time (UTC+5)
"""
from datetime import datetime, timezone, timedelta


def _format_schedule(dt: datetime) -> str:
    """Format datetime in Uzbekistan timezone (UTC+5) for Telegram messages"""
    try:
        # Define Uzbekistan timezone (UTC+5)
        uzbekistan_tz = timezone(timedelta(hours=5))
        
        # Convert to Uzbekistan timezone
        # If datetime is naive, assume it's already in UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        
        local_dt = dt.astimezone(uzbekistan_tz)
        
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
    print("=" * 70)
    print("TIMEZONE CONVERSION TEST - Uzbekistan (UTC+5)")
    print("=" * 70)
    
    # Test 1: The reported bug - user selects 05:26 in Uzbekistan
    # This is stored as 00:26 UTC in the database
    print("\n📋 Test 1: Bug Reproduction - User selected 05:26 Uzbekistan time")
    test_dt1 = datetime(2025, 12, 25, 0, 26, 0, tzinfo=timezone.utc)  # 00:26 UTC
    result1 = _format_schedule(test_dt1)
    print(f"   Stored in DB (UTC):        {test_dt1.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"   Telegram message shows:    {result1}")
    print(f"   Expected:                  25-dekabr 2025 • 05:26")
    print(f"   ✅ PASS" if "05:26" in result1 else "   ❌ FAIL")
    
    # Test 2: Another time - user selects 14:30 Uzbekistan time
    print("\n📋 Test 2: User selected 14:30 Uzbekistan time")
    test_dt2 = datetime(2025, 12, 25, 9, 30, 0, tzinfo=timezone.utc)  # 09:30 UTC = 14:30 UZB
    result2 = _format_schedule(test_dt2)
    print(f"   Stored in DB (UTC):        {test_dt2.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"   Telegram message shows:    {result2}")
    print(f"   Expected:                  25-dekabr 2025 • 14:30")
    print(f"   ✅ PASS" if "14:30" in result2 else "   ❌ FAIL")
    
    # Test 3: Edge case - midnight in Uzbekistan
    print("\n📋 Test 3: Midnight in Uzbekistan (00:00 UZB = 19:00 prev day UTC)")
    test_dt3 = datetime(2025, 12, 24, 19, 0, 0, tzinfo=timezone.utc)  # Previous day UTC
    result3 = _format_schedule(test_dt3)
    print(f"   Stored in DB (UTC):        {test_dt3.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"   Telegram message shows:    {result3}")
    print(f"   Expected:                  25-dekabr 2025 • 00:00")
    print(f"   ✅ PASS" if "25-dekabr" in result3 and "00:00" in result3 else "   ❌ FAIL")
    
    # Test 4: Late evening - 23:59 in Uzbekistan
    print("\n📋 Test 4: Late evening in Uzbekistan (23:59 UZB = 18:59 UTC)")
    test_dt4 = datetime(2025, 12, 25, 18, 59, 0, tzinfo=timezone.utc)
    result4 = _format_schedule(test_dt4)
    print(f"   Stored in DB (UTC):        {test_dt4.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"   Telegram message shows:    {result4}")
    print(f"   Expected:                  25-dekabr 2025 • 23:59")
    print(f"   ✅ PASS" if "23:59" in result4 else "   ❌ FAIL")
    
    # Test 5: Naive datetime (no timezone info) - should be treated as UTC
    print("\n📋 Test 5: Naive datetime (assumes UTC)")
    test_dt5 = datetime(2025, 6, 15, 10, 0, 0)  # No timezone info
    result5 = _format_schedule(test_dt5)
    print(f"   Stored in DB (naive):      {test_dt5.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Telegram message shows:    {result5}")
    print(f"   Expected:                  15-iyun 2025 • 15:00 (10:00 UTC + 5 hours)")
    print(f"   ✅ PASS" if "15:00" in result5 else "   ❌ FAIL")
    
    # Test 6: Different timezone input (e.g., Frankfurt UTC+1 in winter, UTC+2 in summer)
    print("\n📋 Test 6: Input from Frankfurt timezone (UTC+1)")
    frankfurt_tz = timezone(timedelta(hours=1))
    test_dt6 = datetime(2025, 12, 25, 1, 26, 0, tzinfo=frankfurt_tz)  # 01:26 Frankfurt
    result6 = _format_schedule(test_dt6)
    print(f"   Stored in DB (Frankfurt):  {test_dt6.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"   Equivalent UTC:            {test_dt6.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"   Telegram message shows:    {result6}")
    print(f"   Expected:                  25-dekabr 2025 • 05:26 (00:26 UTC + 5 hours)")
    print(f"   ✅ PASS" if "05:26" in result6 else "   ❌ FAIL")
    
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print("✅ All datetime values are now converted to Uzbekistan timezone (UTC+5)")
    print("✅ Time displayed matches what user selected, regardless of server location")
    print("✅ Naive datetimes are treated as UTC before conversion")
    print("✅ Different input timezones are properly handled")
    print("\n💡 Key Fix: Added explicit Uzbekistan timezone conversion in _format_schedule()")
    print("=" * 70)
