"""
GPU Detection Manager
Detects NVIDIA GPUs via nvidia-smi (no torch dependency).
"""
import subprocess
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class GPUInfo:
    """Information about a single GPU."""
    index: int
    name: str
    memory_total_mb: int
    memory_free_mb: int
    uuid: str


class GPUManager:
    """Detects and enumerates GPUs using nvidia-smi."""

    @staticmethod
    def detect_gpus() -> List[GPUInfo]:
        """Detect all NVIDIA GPUs by parsing nvidia-smi CSV output.

        Returns an empty list if nvidia-smi is unavailable or fails.
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,name,memory.total,memory.free,uuid",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []

            gpus = []
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 5:
                    gpus.append(GPUInfo(
                        index=int(parts[0]),
                        name=parts[1],
                        memory_total_mb=int(parts[2]),
                        memory_free_mb=int(parts[3]),
                        uuid=parts[4],
                    ))
            return gpus

        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return []

    @staticmethod
    def get_gpu_display_list() -> List[Tuple[str, str]]:
        """Return a list of (display_label, device_value) tuples.

        Always includes CPU as the first entry.
        """
        items: List[Tuple[str, str]] = [("CPU (no GPU)", "cpu")]
        for gpu in GPUManager.detect_gpus():
            label = f"GPU {gpu.index}: {gpu.name} ({gpu.memory_total_mb} MB)"
            items.append((label, str(gpu.index)))
        return items

    @staticmethod
    def is_nvidia_available() -> bool:
        """Quick check whether nvidia-smi is present and working."""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False
