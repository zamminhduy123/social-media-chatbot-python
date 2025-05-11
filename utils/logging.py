import os
from datetime import datetime

import psutil


def get_system_usage(interval=1):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    process = psutil.Process(os.getpid())
    memory = process.memory_info().rss / 1024 / 1024
    cpu = process.cpu_percent(interval=interval)

    log = f"{current_time}\n" f"CPU Usage: {cpu}%\n" f"Memory Usage: {memory:.2f} MB\n"

    log += "-" * 20
    return log
