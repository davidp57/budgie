"""Reset password for a Budgie user account (dev utility)."""

import getpass
import sqlite3
import sys

import bcrypt


def main() -> None:
    """Prompt for username and new password, then update the DB hash."""
    username = input("Username: ").strip()
    if not username:
        print("Aborted.")
        sys.exit(1)

    conn = sqlite3.connect("data/budgie.db")
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if row is None:
        print(f"User '{username}' not found.")
        conn.close()
        sys.exit(1)

    password = getpass.getpass("New password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords don't match.")
        conn.close()
        sys.exit(1)
    if len(password) < 4:
        print("Password too short (min 4 chars).")
        conn.close()
        sys.exit(1)

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    cur.execute("UPDATE users SET hashed_password = ? WHERE id = ?", (hashed, row[0]))
    conn.commit()
    conn.close()
    print(f"Password updated for '{username}'.")


if __name__ == "__main__":
    main()
