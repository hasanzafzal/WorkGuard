import json
import logging
import os
import queue
import signal
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _load_env_file(path: str) -> None:
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("\"'")
                if key:
                    os.environ[key] = value
    except OSError:
        pass

_load_env_file(os.path.join(BASE_DIR, ".env"))

for _name in ("WORKGUARD_AES_KEY_BASE64", "WORKGUARD_ADMIN_SERVER_URL", "WORKGUARD_TRANSMISSION_INTERVAL_SECONDS"):
    _val = os.getenv(_name)
    if _val:
        print(f"[env] {_name}={_val[:8]}...")

from monitoring.process_monitor import ProcessMonitor
from monitoring.file_monitor import FileMonitor
from monitoring.focus_monitor import FocusMonitor
from monitoring.process_filter import StaticProcessFilter
from network.client import NetworkClient
from security.encryption import key_from_base64
from session_builder.session_builder import SessionBuilder
from storage.sqlite_buffer import SQLiteBuffer


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "monitoring_config.json")
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
SQLITE_DB_PATH = os.path.join(STORAGE_DIR, "employee_buffer.db")
DEFAULT_ADMIN_SERVER_URL = "http://127.0.0.1:8000"
DEFAULT_TRANSMISSION_INTERVAL_SECONDS = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    """Load employee monitoring configuration from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_network_client(sqlite_buffer: SQLiteBuffer):
    """Create the sender from runtime configuration without storing a key."""
    encoded_key = os.getenv("WORKGUARD_AES_KEY_BASE64")

    if not encoded_key:
        _log.warning(
            "WORKGUARD_AES_KEY_BASE64 is not set; sessions will remain pending."
        )
        return None

    try:
        encryption_key = key_from_base64(encoded_key)
    except ValueError as error:
        _log.error(
            "Invalid WORKGUARD_AES_KEY_BASE64; sessions will remain pending: %s", error
        )
        return None

    server_url = os.getenv("WORKGUARD_ADMIN_SERVER_URL", DEFAULT_ADMIN_SERVER_URL)

    return NetworkClient(
        sqlite_buffer=sqlite_buffer,
        encryption_key=encryption_key,
        server_url=server_url,
    )


def get_transmission_retry_interval() -> float:
    """Read a safe periodic retry interval from the environment."""
    configured_value = os.getenv(
        "WORKGUARD_TRANSMISSION_INTERVAL_SECONDS",
        str(DEFAULT_TRANSMISSION_INTERVAL_SECONDS),
    )

    try:
        interval = float(configured_value)
    except ValueError:
        interval = DEFAULT_TRANSMISSION_INTERVAL_SECONDS

    if interval <= 0:
        interval = DEFAULT_TRANSMISSION_INTERVAL_SECONDS

    return interval


def queue_session(
    session_path: str,
    sqlite_buffer: SQLiteBuffer,
    network_client: NetworkClient | None = None,
):
    """Add a finalized session JSON file to the local SQLite buffer."""
    _log.info("New finalized session: %s", session_path)
    success = sqlite_buffer.add_session_from_file(session_path)
    if success:
        _log.info(
            "Session queued for transmission. Pending: %d",
            sqlite_buffer.get_pending_count(),
        )
        if network_client is not None:
            network_client.transmit_pending_sessions()
    else:
        _log.warning("Failed to add session to SQLite buffer: %s", session_path)


def main():
    config = load_config(CONFIG_PATH)
    config["_base_dir"] = BASE_DIR
    config["program_filter"] = StaticProcessFilter(config)

    event_queue = queue.Queue()
    os.makedirs(STORAGE_DIR, exist_ok=True)

    sqlite_buffer = SQLiteBuffer(db_path=SQLITE_DB_PATH)
    _log.info(
        "SQLite buffer: %s  (pending: %d)",
        SQLITE_DB_PATH,
        sqlite_buffer.get_pending_count(),
    )

    network_client = create_network_client(sqlite_buffer)
    if network_client is not None:
        sent_count = network_client.transmit_pending_sessions()
        if sent_count:
            _log.info("Sent %d pending session(s) at startup.", sent_count)

    process_monitor = ProcessMonitor(config, event_queue)
    file_monitor    = FileMonitor(config, event_queue)
    focus_monitor   = FocusMonitor(config, event_queue)

    def on_session_created(session_path: str):
        queue_session(session_path, sqlite_buffer, network_client)

    session_builder = SessionBuilder(
        config,
        event_queue,
        sessions_dir=SESSIONS_DIR,
        on_session_created=on_session_created,
    )
    monitors = [process_monitor, file_monitor, focus_monitor]

    _log.info(
        "System identity: employee_id=%s  employee_name=%s",
        session_builder.employee_id,
        session_builder.employee_name,
    )
    _log.info("Starting session builder and monitors...")

    session_builder.start()         # consumer first
    for monitor in monitors:
        monitor.start()

    _log.info(
        "Monitor threads: %s",
        ", ".join(f"{m.name}={m.is_alive()}" for m in monitors),
    )
    _log.info("Employee monitoring agent is running. Press Ctrl+C to stop.")

    stop_requested = {"flag": False}
    retry_interval = get_transmission_retry_interval()
    next_transmission_attempt = time.monotonic() + retry_interval

    def _handle_signal(signum, frame):
        stop_requested["flag"] = True

    signal.signal(signal.SIGINT, _handle_signal)
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
    except (AttributeError, ValueError):
        pass

    try:
        while not stop_requested["flag"]:
            if (
                network_client is not None
                and time.monotonic() >= next_transmission_attempt
            ):
                network_client.transmit_pending_sessions()
                next_transmission_attempt = time.monotonic() + retry_interval
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_requested["flag"] = True

    _log.info("Shutdown requested. Stopping monitors...")
    for monitor in monitors:
        monitor.stop()
    for monitor in monitors:
        monitor.join(timeout=5)

    _log.info("Finalizing active session and stopping session builder...")
    session_builder.stop()
    session_builder.join(timeout=10)

    _log.info("Pending sessions in SQLite: %d", sqlite_buffer.get_pending_count())
    _log.info("Shutdown complete.")
    _log.info("Sessions saved to: %s", SESSIONS_DIR)
    _log.info("SQLite buffer: %s", SQLITE_DB_PATH)


if __name__ == "__main__":
    main()