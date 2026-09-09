"""
process_filter.py

Static exclusion filter for Windows background processes.

A process is blocked when any of four independent rules match it:

  Rule 1 — Name is in the curated background-process set (O(1) lookup).
  Rule 2 — Executable path starts with a Windows system directory prefix.
  Rule 3 — Executable path contains a known internal-tool fragment
            (VS Code bundled modules, IDE extension bins, vendor agents).
  Rule 4 — Process runs under a Windows service account (best-effort).

Everything else is allowed. Unknown or novel processes are allowed by
default — it is better to log too much than to silently drop activity.

Config keys (all optional):
  "extra_blocked_processes"   list[str]  Additional names to block.
  "filter_by_service_account" bool       Enable Rule 4 (default: True).
"""

import logging

import psutil

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule 1 — curated background-process name set (lower-case)
# ---------------------------------------------------------------------------
_BACKGROUND_PROCESSES: frozenset[str] = frozenset({

    # ── Kernel / pseudo-processes ──────────────────────────────────────────
    "system", "system idle process", "registry",
    "memory compression", "secure system", "vmmem",

    # ── Session & process management ──────────────────────────────────────
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe",
    "lsass.exe", "lsaiso.exe", "lsm.exe", "services.exe", "svchost.exe",

    # ── Desktop composition ────────────────────────────────────────────────
    "dwm.exe", "fontdrvhost.exe",

    # ── Shell infrastructure ───────────────────────────────────────────────
    "sihost.exe", "runtimebroker.exe", "applicationframehost.exe",
    "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "searchhost.exe", "lockapp.exe", "logonui.exe", "userinit.exe",
    "backgroundtaskhost.exe",

    # ── Audio ──────────────────────────────────────────────────────────────
    "audiodg.exe",

    # ── Print spooler ──────────────────────────────────────────────────────
    "spoolsv.exe",

    # ── Task scheduler / COM ───────────────────────────────────────────────
    "taskhost.exe", "taskhostw.exe", "dllhost.exe", "msdtc.exe",
    "conhost.exe",

    # ── Input / IME ────────────────────────────────────────────────────────
    "ctfmon.exe",

    # ── WMI ────────────────────────────────────────────────────────────────
    "wmiprvse.exe", "wmiapsrv.exe", "unsecapp.exe", "wbemhost.exe",

    # ── Windows Defender / security ────────────────────────────────────────
    "msmpeng.exe", "nissrv.exe",
    "securityhealthservice.exe", "securityhealthsystray.exe",
    "msseces.exe",

    # ── Windows Update / servicing ─────────────────────────────────────────
    "wuauclt.exe", "usoclient.exe", "usohost.exe", "tiworker.exe",
    "trustedinstaller.exe", "musnotification.exe", "musnotificationux.exe",
    "wudfhost.exe",
    # Windows Update orchestrator — runs from C:\Windows\UUS\ (not System32)
    "mousocoreworker.exe",
    "usocoreworker.exe",

    # ── Search indexing ────────────────────────────────────────────────────
    "searchindexer.exe", "searchfilterhost.exe", "searchprotocolhost.exe",

    # ── Software protection / licensing ────────────────────────────────────
    "sppsvc.exe", "sppextcomobj.exe",

    # ── Diagnostics / telemetry ────────────────────────────────────────────
    "werfault.exe", "wermgr.exe", "diaghost.exe", "diagsvc.exe",
    "compattelrunner.exe", "devicecensus.exe", "dmclient.exe",

    # ── Hyper-V / virtualisation ──────────────────────────────────────────
    "vmwp.exe", "vmcompute.exe", "wslhost.exe",

    # ── Credential / biometric ────────────────────────────────────────────
    "keycredentialproviderhost.exe", "bioisoenrollmenthost.exe",

    # ── Xbox / Game DVR ────────────────────────────────────────────────────
    "xblgamesave.exe", "gamebarpresencewriter.exe",

    # ── Networking helpers ────────────────────────────────────────────────
    "wmpnetwk.exe", "ipfsvc.exe",

    # ── GPU / display driver background agents ────────────────────────────
    "igfxem.exe", "igfxhk.exe", "igfxtray.exe", "igfxcuiservice.exe",
    "nvdisplay.container.exe", "nvcontainer.exe", "nvtelemetry.exe",
    "nvsvc.exe", "nvsvc32.exe",
    "amdfendrsr.exe", "amdow.exe", "ccc.exe",

    # ── Internet-dependent auto-starters (useless on no-internet LAN) ──────
    "olk.exe", "xpdagent.exe",
    "onedrive.exe", "onedrivesetup.exe",
    "onedrivelauncher.exe",         # OneDrive background launcher

    # ── VS Code / IDE internal processes ─────────────────────────────────
    # These are spawned automatically when VS Code opens — not user apps.
    "openconsole.exe",              # VS Code bundled terminal emulator
    "pet.exe",                      # VS Code Python environment tool

    # ── Python launcher ───────────────────────────────────────────────────
    # py.exe is the Windows Python Launcher — it immediately forks to the
    # real python.exe. It is never the thing doing the actual work and
    # generates redundant start/stop pairs alongside every python.exe event.
    "py.exe",

    # ── Edge WebView (embedded browser, not user-opened) ──────────────────
    "msedgewebview2.exe",

    # ── WPS Office internal agents ────────────────────────────────────────
    "kaideployserver.exe",          # WPS Office add-on deploy server
    "wpscloudsvr.exe",              # WPS cloud sync service
    "wpsoffice.exe",                # WPS background service (not the UI)
})

# ---------------------------------------------------------------------------
# Rule 2 — executable path prefixes (lower-case, no trailing slash)
# Broadened to cover all of C:\Windows, not just System32 subdirs.
# ---------------------------------------------------------------------------
_SYSTEM_DIR_PREFIXES: tuple[str, ...] = (
    r"c:\windows\winsxs",       # Component store
    r"c:\windows\servicing",    # Servicing stack
    r"c:\windows\uus",          # Windows Update orchestrator
    r"c:\windows\temp",         # Windows temp files
)

# ---------------------------------------------------------------------------
# Rule 3 — executable path fragments (lower-case substrings)
# Catches internal tool processes whose name alone does not identify them.
# ---------------------------------------------------------------------------
_INTERNAL_PATH_FRAGMENTS: tuple[str, ...] = (
    # VS Code bundled node modules (OpenConsole, node.exe helpers, etc.)
    r"\node_modules.asar.unpacked\\",
    # VS Code extension-installed binaries (pet.exe, language servers, etc.)
    r"\.vscode-insiders\extensions\\",
    r"\.vscode\extensions\\",
    # OneDrive versioned sub-launcher
    r"\appdata\local\microsoft\onedrive\\",
    # WPS Office internal add-on executables
    r"\appdata\roaming\kingsoft\\",
    r"\appdata\local\kingsoft\\",
    # Logitech Options+ internal agents
    r"\appdata\local\logioptionsplus\\",
)

# ---------------------------------------------------------------------------
# Rule 4 — Windows service accounts
# ---------------------------------------------------------------------------
_SERVICE_ACCOUNTS: frozenset[str] = frozenset({
    "nt authority\\system",
    "nt authority\\local service",
    "nt authority\\network service",
})


class StaticProcessFilter:
    """
    O(1) exclusion filter for Windows background and internal processes.

    All four rules are independent. A process is blocked if *any* rule
    matches. Passing all rules means the process is allowed.

    Thread-safe: holds no mutable state after __init__.
    """

    def __init__(self, config: dict):
        extra: set[str] = {
            str(n).lower()
            for n in config.get("extra_blocked_processes", [])
        }
        self._blocked: frozenset[str] = _BACKGROUND_PROCESSES | extra
        self._check_accounts: bool = config.get("filter_by_service_account", True)

        _log.info(
            "[StaticProcessFilter] %d built-in + %d extra blocked names.",
            len(_BACKGROUND_PROCESSES), len(extra),
        )

    def is_allowed(
        self,
        process_name: str,
        executable: str = "",
        pid: int = 0,
    ) -> bool:
        """
        Return True if this process should contribute events to a session.
        """
        # Rule 1 — static name set
        if process_name.lower() in self._blocked:
            _log.debug("Blocked [name]:     %s", process_name)
            return False

        if executable:
            exe_lower = executable.lower()

            # Rule 2 — system directory prefix
            if any(exe_lower.startswith(p) for p in _SYSTEM_DIR_PREFIXES):
                _log.debug("Blocked [sys path]: %s", process_name)
                return False

            # Rule 3 — internal tool path fragment
            if any(frag in exe_lower for frag in _INTERNAL_PATH_FRAGMENTS):
                _log.debug("Blocked [fragment]: %s  (%s)", process_name, executable)
                return False

        # Rule 4 — service account (best-effort)
        if self._check_accounts and pid:
            try:
                username = (psutil.Process(pid).username() or "").lower()
                if username in _SERVICE_ACCOUNTS:
                    _log.debug("Blocked [svc acct]: %s", process_name)
                    return False
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        _log.debug("Allowed:            %s", process_name)
        return True