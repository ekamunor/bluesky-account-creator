"""Password generator for Bluesky accounts."""

import secrets
import string
from typing import List


def generate_password(
    length: int = 16,
    use_uppercase: bool = True,
    use_lowercase: bool = True,
    use_digits: bool = True,
    use_special: bool = True,
) -> str:
    """
    Generate a secure random password.

    Args:
        length: Length of the password (minimum 12).
        use_uppercase: Include uppercase letters.
        use_lowercase: Include lowercase letters.
        use_digits: Include digits.
        use_special: Include special characters.

    Returns:
        A secure random password string.

    Raises:
        ValueError: If length < 12 or no character types are selected.
    """
    if length < 12:
        raise ValueError("Password length must be at least 12 characters")

    chars = ""
    if use_uppercase:
        chars += string.ascii_uppercase
    if use_lowercase:
        chars += string.ascii_lowercase
    if use_digits:
        chars += string.digits
    if use_special:
        chars += "!@#$%^&*-_=+[]{}()?."

    if not chars:
        raise ValueError("At least one character type must be selected")

    password = "".join(secrets.choice(chars) for _ in range(length))
    return password


def generate_passwords(count: int = 1, length: int = 16) -> List[str]:
    """
    Generate multiple secure passwords.

    Args:
        count: Number of passwords to generate.
        length: Length of each password.

    Returns:
        List of secure random password strings.
    """
    return [generate_password(length=length) for _ in range(count)]


if __name__ == "__main__":
    import sys

    try:
        count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        length = int(sys.argv[2]) if len(sys.argv) > 2 else 16
        passwords = generate_passwords(count=count, length=length)
        for pwd in passwords:
            print(pwd)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)
