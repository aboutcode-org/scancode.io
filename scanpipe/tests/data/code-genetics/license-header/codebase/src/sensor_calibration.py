# Copyright (c) 2026 Greenhouse Collective
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Calibration of the soil moisture sensors of the greenhouse benches."""

from dataclasses import dataclass


@dataclass
class SensorReading:
    sensor_id: str
    raw_value: int


@dataclass
class Calibration:
    dry_value: int
    wet_value: int

    def to_moisture_percent(self, raw_value):
        span = self.dry_value - self.wet_value
        if span <= 0:
            raise ValueError("The dry value must be higher than the wet value.")

        clamped_value = min(max(raw_value, self.wet_value), self.dry_value)
        return round(100 * (self.dry_value - clamped_value) / span)


def calibrate_readings(readings, calibration_by_sensor_id):
    moisture_by_sensor_id = {}
    for reading in readings:
        calibration = calibration_by_sensor_id.get(reading.sensor_id)
        if not calibration:
            continue

        moisture_by_sensor_id[reading.sensor_id] = calibration.to_moisture_percent(
            reading.raw_value
        )
    return moisture_by_sensor_id


def driest_sensor(moisture_by_sensor_id):
    if not moisture_by_sensor_id:
        return

    return min(moisture_by_sensor_id, key=moisture_by_sensor_id.get)
