"""
Generic secret storage via OS keyring.

Uses the `keyring` package to store secrets securely in the OS-native
credential store (Windows Credential Locker / macOS Keychain / Linux
Secret Service). Not tied to any single secret — callers identify secrets
by `key_name` (e.g. "google_api_key").

Install dependency: pip install keyring
"""

import keyring
import keyring.errors

_SERVICE_NAME = "SurveyCTO Convertor"


def get_secret(key_name: str) -> str | None:
    """Return the stored secret for `key_name`, or None if not set."""
    return keyring.get_password(_SERVICE_NAME, key_name)


def set_secret(key_name: str, value: str) -> None:
    """Store `value` under `key_name` in the OS keyring."""
    keyring.set_password(_SERVICE_NAME, key_name, value)


def delete_secret(key_name: str) -> None:
    """Remove the stored secret for `key_name`, if present."""
    try:
        keyring.delete_password(_SERVICE_NAME, key_name)
    except keyring.errors.PasswordDeleteError:
        pass


def has_secret(key_name: str) -> bool:
    """True if a secret is currently stored under `key_name`."""
    return get_secret(key_name) is not None