from app.services.phone import normalize_phone


def test_normalize_phone_valid_formats():
    assert normalize_phone("+998901234567") == "+998901234567"
    assert normalize_phone("998901234567") == "+998901234567"
    assert normalize_phone("90 123 45 67") == "+998901234567"
    assert normalize_phone("(90)1234567") == "+998901234567"
    assert normalize_phone("0901234567") == "+998901234567"


def test_normalize_phone_invalid_formats():
    assert normalize_phone("") is None
    assert normalize_phone("123") is None
    assert normalize_phone("+997901234567") is None
    assert normalize_phone("99890123456") is None
