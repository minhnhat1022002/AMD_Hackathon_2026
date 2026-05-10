"""Run ota-crawl and hospitality_ai API together for local development."""

from __future__ import annotations

import os
import shlex
import signal
import subprocess
import sys
import threading
from datetime import date, timedelta
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
OTA_CRAWL_DIR = ROOT_DIR / "ota-crawl"
SRC_DIR = ROOT_DIR / "src"
DEFAULT_VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"
DEFAULT_OWN_HOTEL_ID = "119242771"
DEFAULT_TRIP_HOTEL_URLS = ",".join(
    [
        (
            "https://vn.trip.com/hotels/ho-chi-minh-city-hotel-detail-"
            "119242771/kin-hotel-dong-du/"
        ),
        (
            "https://vn.trip.com/hotels/ho-chi-minh-city-hotel-detail-"
            "714552/silverland-jolie-ho-chi-minh-city/"
        ),
        (
            "https://vn.trip.com/hotels/ho-chi-minh-city-hotel-detail-"
            "51072951/icon-saigon-luxury-design-hotel/"
        ),
        (
            "https://vn.trip.com/hotels/ho-chi-minh-city-hotel-detail-"
            "993083/bong-sen-hotel-saigon/"
        ),
    ]
)


def main() -> int:
    """Start both local services and stop them together."""

    ota_port = os.getenv("OTA_CRAWL_PORT", "8000")
    hospitality_port = os.getenv("HOSPITALITY_API_PORT", "8100")

    ota_env = _build_base_env()
    hospitality_env = _build_base_env()
    hospitality_env.setdefault("HOSPITALITY_CRAWLER_SOURCE", "trip-api")
    hospitality_env.setdefault("HOSPITALITY_TRIP_PRICE_API_MODE", "http")
    hospitality_env.setdefault(
        "HOSPITALITY_TRIP_PRICE_API_BASE_URL",
        f"http://localhost:{ota_port}",
    )
    hospitality_env.setdefault(
        "HOSPITALITY_OWN_HOTEL_ID",
        DEFAULT_OWN_HOTEL_ID,
    )
    hospitality_env.setdefault(
        "HOSPITALITY_TRIP_HOTEL_URLS",
        DEFAULT_TRIP_HOTEL_URLS,
    )
    today = date.today()
    hospitality_env.setdefault(
        "HOSPITALITY_TRIP_CHECK_IN_DATES",
        today.isoformat(),
    )
    hospitality_env.setdefault(
        "HOSPITALITY_TRIP_CHECK_OUT_DATE",
        (today + timedelta(days=1)).isoformat(),
    )

    processes = [
        _start_process(
            name="ota-crawl",
            command=_ota_command(ota_port),
            env=ota_env,
        ),
        _start_process(
            name="hospitality-api",
            command=_hospitality_command(hospitality_port),
            env=hospitality_env,
        ),
    ]

    print("")
    print("Services started:")
    print(f"- ota-crawl:       http://localhost:{ota_port}")
    print(f"- hospitality API: http://localhost:{hospitality_port}")
    print("")
    print("Useful checks:")
    print(f"- curl http://localhost:{ota_port}/v1/prices/sources")
    print(f"- curl http://localhost:{hospitality_port}/pricing-insight")
    print("")
    print("Press Ctrl+C to stop both services.")

    try:
        return _wait_until_one_exits(processes)
    except KeyboardInterrupt:
        print("\nStopping services...")
        return 130
    finally:
        _terminate_all(processes)


def _build_base_env() -> dict[str, str]:
    env = os.environ.copy()
    pythonpath_parts = [
        str(ROOT_DIR),
        str(SRC_DIR),
        str(OTA_CRAWL_DIR),
        env.get("PYTHONPATH", ""),
    ]
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in pythonpath_parts if part
    )
    return env


def _ota_command(port: str) -> list[str]:
    custom_command = os.getenv("OTA_CRAWL_COMMAND")
    if custom_command:
        return shlex.split(custom_command)

    return [
        _python_executable(),
        "-m",
        "uvicorn",
        "main:app",
        "--app-dir",
        str(OTA_CRAWL_DIR),
        "--host",
        "0.0.0.0",
        "--port",
        port,
    ]


def _hospitality_command(port: str) -> list[str]:
    custom_command = os.getenv("HOSPITALITY_API_COMMAND")
    if custom_command:
        return shlex.split(custom_command)

    return [
        _python_executable(),
        "-m",
        "uvicorn",
        "hospitality_ai.interfaces.api:create_app",
        "--factory",
        "--host",
        "0.0.0.0",
        "--port",
        port,
    ]


def _python_executable() -> str:
    configured = os.getenv("SERVICES_PYTHON")
    if configured:
        return configured
    if DEFAULT_VENV_PYTHON.exists():
        return str(DEFAULT_VENV_PYTHON)
    return sys.executable


def _start_process(
    name: str,
    command: list[str],
    env: dict[str, str],
) -> subprocess.Popen[str]:
    print(f"Starting {name}: {' '.join(command)}")
    process = subprocess.Popen(
        command,
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    thread = threading.Thread(
        target=_stream_output,
        args=(name, process),
        daemon=True,
    )
    thread.start()
    return process


def _stream_output(name: str, process: subprocess.Popen[str]) -> None:
    if process.stdout is None:
        return
    for line in process.stdout:
        print(f"[{name}] {line}", end="")


def _wait_until_one_exits(processes: list[subprocess.Popen[str]]) -> int:
    while True:
        for process in processes:
            return_code = process.poll()
            if return_code is not None:
                return return_code
        threading.Event().wait(0.5)


def _terminate_all(processes: list[subprocess.Popen[str]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)

    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
