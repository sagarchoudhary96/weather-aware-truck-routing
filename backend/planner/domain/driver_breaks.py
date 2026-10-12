"""When must the driver stop, and what is the real clock time at any point of the trip?

US Hours of Service (HOS) for one driver who starts fully rested:
- 30-minute break after 8 hours of driving.
- 10-hour rest after 11 hours of driving.

Two clocks: driving time (only while moving) and the trip clock (since departure,
including stops). Example for 12 h of driving: drive 8 h → 30 min break → drive 3 h →
10 h rest → drive 1 h. Trip clock at the end = 12 + 0.5 + 10 = 22.5 h.

The 14-hour duty window never binds here (11 h driving + 0.5 h break < 14 h), and a
single US trip stays under the 70-hour weekly cap, so neither is modelled.
"""

from dataclasses import dataclass
from typing import Literal

HOUR = 3600
BREAK_AFTER_DRIVING_S = 8 * HOUR
BREAK_S = 30 * 60
MAX_DRIVING_S = 11 * HOUR
REST_S = 10 * HOUR


@dataclass(frozen=True)
class Stop:
    kind: Literal["break", "rest"]
    at_drive_s: float  # cumulative driving time when the stop begins
    duration_s: float


@dataclass(frozen=True)
class DriverBreakPlan:
    """The required stops for a trip, and conversions between driving time and the trip clock."""

    stops: list[Stop]

    @classmethod
    def for_total_driving_time(cls, total_drive_s: float, apply_hos: bool = True) -> "DriverBreakPlan":
        """Which stops does a trip with this much driving need?

        Examples: 8 h → none; 9 h → break at 8 h; 12 h → break at 8 h, rest at 11 h;
        25 h → break 8 h, rest 11 h, break 19 h, rest 22 h.
        """
        if not apply_hos:
            return cls([])
        stops: list[Stop] = []
        cycle_start = 0.0
        # A stop is only needed if driving continues past the limit.
        while cycle_start + BREAK_AFTER_DRIVING_S < total_drive_s:
            stops.append(Stop("break", cycle_start + BREAK_AFTER_DRIVING_S, BREAK_S))
            if cycle_start + MAX_DRIVING_S >= total_drive_s:
                break
            stops.append(Stop("rest", cycle_start + MAX_DRIVING_S, REST_S))
            cycle_start += MAX_DRIVING_S
        return cls(stops)

    def trip_clock_after_driving(self, drive_s: float) -> float:
        """Trip clock when the truck has driven `drive_s`: driving time plus the stops already taken.

        Used for checkpoint ETAs. Example (12 h trip): 9 h of driving → 9.5 h on the trip clock.
        A point reached exactly when a stop starts is reached before that stop.
        """
        return drive_s + sum(s.duration_s for s in self.stops if s.at_drive_s < drive_s)

    def trip_clock_when_stop_starts(self, stop: Stop) -> float:
        """Example (12 h trip): the rest after 11 h of driving starts at 11.5 h on the trip clock."""
        return stop.at_drive_s + sum(s.duration_s for s in self.stops if s.at_drive_s < stop.at_drive_s)

    def driving_completed_at(self, elapsed_s: float) -> float:
        """The reverse: how much driving is done at a trip-clock time? It stays constant during stops.

        Used to place the truck on the slider. Example (12 h trip): 8.2 h → 8 h (on break);
        15 h → 11 h (resting); 22 h → 11.5 h.
        """
        offset = 0.0
        for stop in self.stops:
            start = stop.at_drive_s + offset
            if elapsed_s <= start:
                break
            if elapsed_s < start + stop.duration_s:
                return stop.at_drive_s
            offset += stop.duration_s
        return elapsed_s - offset

    @property
    def total_break_time_s(self) -> float:
        return sum(s.duration_s for s in self.stops)
