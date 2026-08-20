# src/config/user_names.py
# Central name mapping — import this wherever user_id is displayed

USER_NAMES = {
    1:  "Anika Banerjee",
    2:  "Rohit Sharma",
    3:  "Amit Patel",
    4:  "Priya Singh",
    5:  "Pooja Shah",
    6:  "Neha Kapoor",
    7:  "Vikram Malhotra",
    8:  "Sanjay Gupta",
    9:  "Ritu Agarwal",
    10: "Rajesh Kumar",
    11: "Suman Choudhary",
    12: "Arjun Reddy",
    13: "Deepak Joshi",
    14: "Sandeep Deshmukh",
    15: "Rohan Chatterjee",
    16: "Anjali Desai",
    17: "Sunita Yadav",
    18: "Priya Nair",
    19: "Kavita Verma",
    20: "Deepika Bansal",
}


def get_name(user_id: int) -> str:
    """Returns display name for a user_id. Falls back to 'User {id}' if not found."""
    return USER_NAMES.get(int(user_id), f"User {user_id}")


def get_id(name: str) -> int:
    """Reverse lookup — name → user_id."""
    for uid, uname in USER_NAMES.items():
        if uname == name:
            return uid
    raise ValueError(f"Name '{name}' not found in USER_NAMES")


def all_names() -> list:
    """Returns list of all names in user_id order."""
    return [USER_NAMES[i] for i in sorted(USER_NAMES.keys())]