"""
Unit tests for validators.
"""
from validators import (
    clean_text,
    normalize_phone,
    normalize_date,
    validate_age,
    normalize_gender,
    normalize_id_proof_type,
    validate_id_proof_last4,
    validate_donation,
)

def test_clean_text():
    assert clean_text("  hello world  ") == "hello world"
    assert clean_text(None) == ""
    assert clean_text(123) == "123"

def test_normalize_phone():
    phone, valid = normalize_phone("9848022338")
    assert valid is True
    assert phone == "9848022338"

    phone, valid = normalize_phone("+91 98480 22338")
    assert valid is True
    assert phone == "9848022338"

    phone, valid = normalize_phone("09848022338")
    assert valid is True
    assert phone == "9848022338"

    phone, valid = normalize_phone("9XXXXXXXXX")
    assert valid is True
    assert phone == "9XXXXXXXXX"

    phone, valid = normalize_phone("12345")
    assert valid is False

    phone, valid = normalize_phone("")
    assert valid is True
    assert phone == ""

def test_normalize_date():
    dt, valid = normalize_date("2026-12-25")
    assert valid is True
    assert dt == "2026-12-25"

    dt, valid = normalize_date("25-12-2026")
    assert valid is True
    assert dt == "2026-12-25"

    dt, valid = normalize_date("25/12/2026")
    assert valid is True
    assert dt == "2026-12-25"

    dt, valid = normalize_date("invalid-date")
    assert valid is False

    dt, valid = normalize_date("")
    assert valid is True
    assert dt == ""

def test_validate_age():
    age, valid = validate_age(45)
    assert valid is True
    assert age == 45

    age, valid = validate_age("50.0")
    assert valid is True
    assert age == 50

    age, valid = validate_age(150)
    assert valid is False

    age, valid = validate_age(-5)
    assert valid is False

    age, valid = validate_age("")
    assert valid is True
    assert age is None

def test_normalize_gender():
    assert normalize_gender("m") == "Male"
    assert normalize_gender("MALE") == "Male"
    assert normalize_gender("female") == "Female"
    assert normalize_gender("f") == "Female"
    assert normalize_gender("Other") == "Other"

def test_normalize_id_proof_type():
    assert normalize_id_proof_type("aadhaar card") == "Aadhaar"
    assert normalize_id_proof_type("passport") == "Passport"
    assert normalize_id_proof_type("voter id") == "Voter ID"
    assert normalize_id_proof_type("dl") == "Driving License"

def test_validate_id_proof_last4():
    last4, valid = validate_id_proof_last4("1234")
    assert valid is True
    assert last4 == "1234"

    # Full 12-digit Aadhaar input should protect user by truncating to last 4
    last4, valid = validate_id_proof_last4("123456789012")
    assert valid is True
    assert last4 == "9012"

    last4, valid = validate_id_proof_last4("")
    assert valid is True
    assert last4 == ""

def test_validate_donation():
    amt, valid = validate_donation(10000)
    assert valid is True
    assert amt == 10000.0

    amt, valid = validate_donation("25000.50")
    assert valid is True
    assert amt == 25000.50

    amt, valid = validate_donation(-100)
    assert valid is False

    amt, valid = validate_donation("")
    assert valid is True
    assert amt == 10000.0
