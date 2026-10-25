"""Admin-configurable settings stored in the database with safe defaults."""
import copy

DEFAULTS = {
    "match_weights": {"category": 0.20, "text": 0.25, "location": 0.20, "date": 0.15, "visual": 0.20},
    "match_threshold": 0.35,
    "match_notify_threshold": 0.60,
    "report_expiry_days": 60,
    "notify_on_match": True,
    "notify_on_comment": True,
    "notify_on_message": True,
    "require_report_approval": False,
}


def get_setting(key):
    from .models import SiteSetting
    row = SiteSetting.objects.filter(key=key).first()
    return row.value if row else copy.deepcopy(DEFAULTS[key])


def all_settings():
    return {k: get_setting(k) for k in DEFAULTS}


def validate_setting(key, value):
    """Return a cleaned value or raise ValueError."""
    if key not in DEFAULTS:
        raise ValueError(f"Unknown setting '{key}'.")
    if key == "match_weights":
        if not isinstance(value, dict) or set(value) != set(DEFAULTS["match_weights"]):
            raise ValueError("match_weights needs keys: category, text, location, date, visual.")
        cleaned = {k: float(v) for k, v in value.items()}
        if any(v < 0 for v in cleaned.values()) or sum(cleaned.values()) <= 0:
            raise ValueError("Weights must be non-negative and not all zero.")
        return cleaned
    if key in ("match_threshold", "match_notify_threshold"):
        v = float(value)
        if not 0 <= v <= 1:
            raise ValueError("Thresholds must be between 0 and 1.")
        return v
    if key == "report_expiry_days":
        v = int(value)
        if not 1 <= v <= 3650:
            raise ValueError("Expiry must be between 1 and 3650 days.")
        return v
    return bool(value)
