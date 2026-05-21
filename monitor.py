import os
from dataclasses import dataclass
from typing import Optional

import psutil
import requests
from dotenv import load_dotenv


@dataclass(frozen=True)
class Metric:
    name: str
    value: Optional[float]
    threshold: float
    unit: str

    @property
    def exceeded(self) -> bool:
        return self.value is not None and self.value > self.threshold


@dataclass(frozen=True)
class DiskMetric:
    mountpoint: str
    percent: float
    free_bytes: int
    threshold: float

    @property
    def exceeded(self) -> bool:
        return self.percent > self.threshold


def read_float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    return float(raw_value)


def get_cpu_temperature() -> Optional[float]:
    sensors = psutil.sensors_temperatures(fahrenheit=False)
    if not sensors:
        return None

    preferred_labels = ("coretemp", "cpu_thermal", "k10temp", "acpitz")
    for label in preferred_labels:
        entries = sensors.get(label)
        if not entries:
            continue
        for entry in entries:
            if entry.current is not None:
                return float(entry.current)

    for entries in sensors.values():
        for entry in entries:
            if entry.current is not None:
                return float(entry.current)

    return None


def collect_metrics() -> list[Metric]:
    cpu_usage = psutil.cpu_percent(interval=1)
    cpu_temperature = get_cpu_temperature()
    ram_usage = psutil.virtual_memory().percent
    memory_usage = psutil.swap_memory().percent

    return [
        Metric("CPU usage", cpu_usage, read_float_env("CPU_USAGE_THRESHOLD", 80.0), "%"),
        Metric("CPU temperature", cpu_temperature, read_float_env("CPU_HEAT_THRESHOLD", 85.0), "C"),
        Metric("RAM usage", ram_usage, read_float_env("RAM_USAGE_THRESHOLD", 80.0), "%"),
        Metric("Memory usage", memory_usage, read_float_env("MEMORY_USAGE_THRESHOLD", 50.0), "%"),
    ]


def collect_disk_metrics() -> list[DiskMetric]:
    disk_threshold = read_float_env("DISK_USAGE_THRESHOLD", 85.0)
    disk_metrics: list[DiskMetric] = []
    seen_mountpoints: set[str] = set()

    for partition in psutil.disk_partitions(all=False):
        if partition.mountpoint in seen_mountpoints:
            continue
        seen_mountpoints.add(partition.mountpoint)

        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except PermissionError:
            continue
        except FileNotFoundError:
            continue

        disk_metrics.append(
            DiskMetric(
                mountpoint=partition.mountpoint,
                percent=usage.percent,
                free_bytes=usage.free,
                threshold=disk_threshold,
            )
        )

    return disk_metrics


def format_metric(metric: Metric) -> str:
    if metric.value is None:
        return f"{metric.name}: unavailable"
    return f"{metric.name}: {metric.value:.1f}{metric.unit} (threshold {metric.threshold:.1f}{metric.unit})"


def format_disk_metric(metric: DiskMetric) -> str:
    free_gb = metric.free_bytes / (1024 ** 3)
    return (
        f"Disk {metric.mountpoint}: {metric.percent:.1f}% used, "
        f"{free_gb:.1f} GiB free (threshold {metric.threshold:.1f}%)"
    )


def build_alert_message(metrics: list[Metric]) -> str:
    lines = ["Server limit alert", ""]
    for metric in metrics:
        lines.append(format_metric(metric))
    return "\n".join(lines)


def build_disk_alert_lines(metrics: list[DiskMetric]) -> list[str]:
    lines = ["Server limit alert", ""]
    for metric in metrics:
        lines.append(format_disk_metric(metric))
    return lines


def send_telegram_message(token: str, user_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": user_id,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    response.raise_for_status()


def main() -> None:
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    user_id = os.getenv("TELEGRAM_USER_ID")

    if not token or not user_id:
        raise SystemExit("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_USER_ID in the environment.")

    metrics = collect_metrics()
    exceeded_metrics = [metric for metric in metrics if metric.exceeded]
    disk_metrics = collect_disk_metrics()
    exceeded_disk_metrics = [metric for metric in disk_metrics if metric.exceeded]

    for metric in metrics:
        print(format_metric(metric))

    for disk_metric in disk_metrics:
        print(format_disk_metric(disk_metric))

    alert_lines: list[str] = []
    if exceeded_metrics:
        alert_lines.extend(build_alert_message(exceeded_metrics).splitlines())
    if exceeded_disk_metrics:
        if alert_lines:
            alert_lines.append("")
        alert_lines.extend(build_disk_alert_lines(exceeded_disk_metrics))

    if alert_lines:
        send_telegram_message(token, user_id, "\n".join(alert_lines))


if __name__ == "__main__":
    main()