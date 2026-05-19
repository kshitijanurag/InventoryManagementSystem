import time
import threading

PROFILING_ENABLED = True

_SLOW_THRESHOLD_S = 0.5
_WARN_THRESHOLD_S = 0.1


class PerfTimer:
    def __init__(self, name: str, *, enabled: bool | None = None):
        self._name = name
        self._on = PROFILING_ENABLED if enabled is None else enabled
        self._t0 = time.perf_counter()
        self._last = self._t0
        self._lock = threading.Lock()
        self._rows: list[tuple[float, float, str]] = []
        if self._on:
            self._emit(0.0, 0.0, "START")

    def checkpoint(self, label: str) -> float:
        if not self._on:
            return 0.0
        now = time.perf_counter()
        with self._lock:
            delta = now - self._last
            elapsed = now - self._t0
            self._last = now
            self._rows.append((elapsed, delta, label))
        self._emit(elapsed, delta, label)
        return delta

    def done(self) -> float:
        if not self._on:
            return 0.0
        now = time.perf_counter()
        total = now - self._t0
        self._emit(total, now - self._last, f"DONE  (total {total:.3f}s)")
        self._print_summary(total)
        return total

    def _emit(self, elapsed: float, delta: float, label: str) -> None:
        flag = ""
        if delta >= _SLOW_THRESHOLD_S:
            flag = "  ← SLOW"
        elif delta >= _WARN_THRESHOLD_S:
            flag = "  △"
        prefix = f"[perf | {self._name}]"
        if delta > 0:
            print(
                f"{prefix}  {elapsed:7.3f}s  {label:<45} (+{delta:.3f}s){flag}",
                flush=True,
            )
        else:
            print(f"{prefix}  {elapsed:7.3f}s  {label}", flush=True)

    def _print_summary(self, total: float) -> None:
        if not self._rows:
            return
        slowest = max(self._rows, key=lambda r: r[1])
        prefix = f"[perf | {self._name}]"
        print(
            f"{prefix}  SLOWEST checkpoint: '{slowest[2]}' took {slowest[1]:.3f}s",
            flush=True,
        )
