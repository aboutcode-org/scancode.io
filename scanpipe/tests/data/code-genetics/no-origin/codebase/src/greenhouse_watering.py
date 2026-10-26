"""Watering plan for the community greenhouse benches."""

from dataclasses import dataclass
from datetime import date
from datetime import timedelta


@dataclass
class Bench:
    label: str
    soil_moisture_percent: int
    last_watered_on: date
    drought_tolerant: bool = False


def watering_interval(bench):
    if bench.drought_tolerant:
        return timedelta(days=6)

    if bench.soil_moisture_percent < 25:
        return timedelta(days=1)

    return timedelta(days=3)


def next_watering_date(bench):
    return bench.last_watered_on + watering_interval(bench)


def benches_due_on(benches, target_date):
    return [bench for bench in benches if next_watering_date(bench) <= target_date]


def format_watering_plan(benches, target_date):
    due_benches = benches_due_on(benches, target_date)
    if not due_benches:
        return f"No bench to water on {target_date:%A %d %B}."

    bench_labels = ", ".join(sorted(bench.label for bench in due_benches))
    return f"Water on {target_date:%A %d %B}: {bench_labels}."
