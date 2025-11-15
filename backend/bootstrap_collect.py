import time
from .collector.fetch_weather import run_once

DEF_RUNS = 500
DEF_SLEEP_SECONDS = 10


def main(runs: int = DEF_RUNS, sleep_seconds: int = DEF_SLEEP_SECONDS) -> None:
    """Bootstrap collector in batch (Mode B).

    Runs the async collector multiple times in a loop so that
    each city accumulates enough records for initial training.
    """
    for i in range(1, runs + 1):
        print(f"[Bootstrap] Run {i}/{runs}...")
        try:
            run_once()
        except Exception as exc:
            print(f"[Bootstrap] Run {i} failed: {exc}")
        if i < runs:
            time.sleep(sleep_seconds)


if __name__ == "__main__":
    # default: 60 lần, nghỉ 10s giữa mỗi lần
    main()
