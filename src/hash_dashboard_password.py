#!/usr/bin/env python3
"""Generate a password hash for BSC_DASHBOARD_USERS."""

import getpass
import hashlib
import os


def main():
    password = getpass.getpass("Dashboard password: ")
    salt = os.urandom(16)
    iterations = 260000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    print(f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}")


if __name__ == "__main__":
    main()
