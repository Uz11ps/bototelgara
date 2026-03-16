from __future__ import annotations


def normalize_phone(phone: str | None) -> str:
    """Normalize a phone number for reliable matching."""
    if not phone:
        return ""

    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits


def phones_match(a: str | None, b: str | None) -> bool:
    """Compare phones by their last 10 digits."""
    left = normalize_phone(a)
    right = normalize_phone(b)
    if not left or not right:
        return False

    left_tail = left[-10:] if len(left) >= 10 else left
    right_tail = right[-10:] if len(right) >= 10 else right
    return left_tail == right_tail
