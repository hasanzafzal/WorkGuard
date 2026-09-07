"""Resolve a stable, local identity for the monitored Windows system."""

import getpass
import hashlib
import os
import platform
import uuid


def _machine_identifier() -> str:
    """Return a stable local machine value without sending the raw value."""
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            ) as key:
                return winreg.QueryValueEx(key, "MachineGuid")[0]
        except OSError:
            pass

    # Fallback for non-Windows systems or restricted Windows registries.
    return f"{platform.node()}:{uuid.getnode()}"


def resolve_employee_identity(config: dict) -> tuple[str, str]:
    """Return configured overrides or a machine-specific ID and display name."""
    configured_id = config.get("employee_id")
    configured_name = config.get("employee_name")
    if configured_id and configured_name:
        return configured_id, configured_name

    machine_hash = hashlib.sha256(
        _machine_identifier().encode("utf-8")
    ).hexdigest()[:12].upper()
    hostname = platform.node() or "Unknown system"
    username = getpass.getuser() or "Unknown user"

    return f"SYS-{machine_hash}", f"{hostname} ({username})"
