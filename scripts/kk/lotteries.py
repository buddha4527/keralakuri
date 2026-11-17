"""Known Kerala State lotteries. Weekday: Monday=0 ... Sunday=6.

If the department renames a lottery or adds a new one, add it here.
Unknown lotteries (e.g. bumpers) still work: they get a slug from their name.
"""
import re

WEEKLY = {
    "BT": {"name": "Bhagyathara", "weekday": 0},
    "SS": {"name": "Sthree Sakthi", "weekday": 1},
    "DL": {"name": "Dhanalekshmi", "weekday": 2},
    "KN": {"name": "Karunya Plus", "weekday": 3},
    "SK": {"name": "Suvarna Keralam", "weekday": 4},
    "KR": {"name": "Karunya", "weekday": 5},
    "SM": {"name": "Samrudhi", "weekday": 6},
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def display_name(code, raw_name):
    if code in WEEKLY:
        return WEEKLY[code]["name"]
    # "THIRUVONAM BUMPER" -> "Thiruvonam Bumper"
    return " ".join(w.capitalize() for w in re.split(r"[\s\-]+", raw_name.strip()) if w)
