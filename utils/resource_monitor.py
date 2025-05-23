import logging
import os
from typing import Dict

import psutil


class ResourceMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_system_resources(self) -> Dict[str, float]:
        """Zwraca aktualny stan zasobów systemowych"""
        try:
            # Użyj głównego dysku systemowego
            disk_path = os.path.abspath(os.sep)  # '/' na Linux, 'C:\' na Windows

            return {
                "cpu": psutil.cpu_percent(interval=0),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage(disk_path).percent,
            }
        except Exception as e:
            self.logger.error(f"Błąd odczytu zasobów systemowych: {str(e)}")
            return {"cpu": 0, "memory": 0, "disk": 0}

    def should_start_render(self) -> bool:
        """Określa czy system jest gotowy do rozpoczęcia renderingu"""
        resources = self.get_system_resources()

        # Proste heurystyki - można rozbudować
        if resources["cpu"] > 90:
            return False
        if resources["memory"] > 85:
            return False
        if resources["disk"] > 95:
            return False

        return True

    def get_optimal_thread_count(self) -> int:
        """Zwraca optymalną liczbę wątków do renderingu"""
        cpu_count = psutil.cpu_count(logical=False)
        memory_gb = psutil.virtual_memory().total / (1024**3)

        # Prosty algorytm - można dostosować
        if memory_gb < 8:
            return max(1, cpu_count - 2)
        elif memory_gb < 16:
            return max(1, cpu_count - 1)
        else:
            return cpu_count
