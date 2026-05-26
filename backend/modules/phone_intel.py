"""
Phone number intelligence via libphonenumber — keyless parsing and validation.
"""
from __future__ import annotations

from typing import Any

try:
    import phonenumbers
    from phonenumbers import carrier, geocoder, timezone
    from phonenumbers.phonenumberutil import NumberParseException
except ImportError:
    phonenumbers = None  # type: ignore[assignment]


def phone_intel_lookup(number: str, default_region: str = "US") -> dict[str, Any]:
    """
    Parse and enrich a phone number (E.164 preferred; region hint optional).
    """
    raw = (number or "").strip()
    if not raw:
        return {"success": False, "error": "Phone number is required", "number": raw}

    if phonenumbers is None:
        return {
            "success": False,
            "error": "phonenumbers package required",
            "number": raw,
        }

    try:
        parsed = phonenumbers.parse(raw, default_region if not raw.startswith("+") else None)
    except NumberParseException as e:
        return {"success": False, "error": str(e), "number": raw}

    valid = phonenumbers.is_valid_number(parsed)
    possible = phonenumbers.is_possible_number(parsed)
    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    national = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    intl = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)

    num_type = phonenumbers.number_type(parsed)
    type_names = {
        0: "fixed_line",
        1: "mobile",
        2: "fixed_line_or_mobile",
        3: "toll_free",
        4: "premium_rate",
        5: "shared_cost",
        6: "voip",
        7: "personal_number",
        8: "pager",
        9: "uan",
        10: "voicemail",
        -1: "unknown",
    }

    region = phonenumbers.region_code_for_number(parsed)
    loc = geocoder.description_for_number(parsed, "en") if valid else ""
    car = carrier.name_for_number(parsed, "en") if valid else ""
    tzs = list(timezone.time_zones_for_number(parsed)) if valid else []

    return {
        "success": True,
        "number": raw,
        "e164": e164,
        "national": national,
        "international": intl,
        "country_code": parsed.country_code,
        "national_number": str(parsed.national_number),
        "region": region,
        "valid": valid,
        "possible": possible,
        "type": type_names.get(num_type, "unknown"),
        "location": loc,
        "carrier": car,
        "timezones": tzs,
    }
