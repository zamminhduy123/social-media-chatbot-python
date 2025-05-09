import psutil
from datetime import datetime


def get_system_usage(interval:float=1):
    cpu = psutil.cpu_percent(interval=interval)
    memory = psutil.virtual_memory()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log = (
        f"{current_time}\n"
        f"CPU Usage: {cpu}%\n"
        f"Memory Usage: {memory.percent}% ({memory.used / (1024**3):.2f} GB used of {memory.total / (1024**3):.2f} GB)\n"
    )

    log += "-" * 20
    return log
