
from datetime import datetime, timezone
from time import monotonic_ns, time_ns


class ClockConverter:
    def __init__(self):
        before = monotonic_ns()
        utc_now = time_ns()
        after = monotonic_ns()

        monotonic_now = (before + after) // 2

        self.offset_ns = utc_now - monotonic_now

    def to_utc(self, timestamp_ns: int) -> str:
        utc_ns = timestamp_ns + self.offset_ns

        seconds, nanoseconds = divmod(
            utc_ns, 1_000_000_000
        )

        date = datetime.fromtimestamp(
            seconds,
            tz=timezone.utc
        )

        date = date.replace(
            microsecond=nanoseconds // 1_000
        )

        return date.isoformat(
            timespec="microseconds"
        ).replace("+00:00", "Z")
