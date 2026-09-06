from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any


def get_system_info() -> dict[str, Any]:
    """Collect detailed local Windows system information."""

    info: dict[str, Any] = {
        "os": platform.platform(),
        "computer_name": platform.node(),
        "python_version": platform.python_version(),
        "cpu": platform.processor(),
    }

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    try:
        output = subprocess.check_output(
            ["wmic", "cpu", "get", "Name", "/value"],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in output.splitlines():
            if line.startswith("Name="):
                info["cpu"] = line.split("=", 1)[1].strip()
                break

    except Exception:
        pass

    # --------------------------------------------------------
    # RAM
    # --------------------------------------------------------

    try:
        output = subprocess.check_output(
            [
                "wmic",
                "computersystem",
                "get",
                "TotalPhysicalMemory",
                "/value",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        for line in output.splitlines():
            if line.startswith("TotalPhysicalMemory="):
                raw_value = line.split("=", 1)[1].strip()

                if raw_value:
                    total_bytes = int(raw_value)

                    info["ram_gb"] = round(
                        total_bytes / (1024 ** 3),
                        2,
                    )

                break

    except Exception:
        pass

    # --------------------------------------------------------
    # NVIDIA GPU
    # --------------------------------------------------------

    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )

        gpus = []

        for line in output.splitlines():
            parts = [part.strip() for part in line.split(",")]

            if len(parts) >= 3:
                gpus.append(
                    {
                        "name": parts[0],
                        "vram": parts[1],
                        "driver": parts[2],
                    }
                )

        info["nvidia_gpus"] = gpus

    except Exception:
        info["nvidia_gpus"] = []

    # --------------------------------------------------------
    # Disk
    # --------------------------------------------------------

    try:
        total, used, free = shutil.disk_usage(
            os.path.abspath(os.sep)
        )

        info["disk"] = {
            "total_gb": round(total / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
        }

    except Exception:
        pass

    return info


if __name__ == "__main__":
    import json

    result = get_system_info()

    print(
        json.dumps(
            result,
            indent=2,
        )
    )
