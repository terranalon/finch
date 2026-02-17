"""Benchmark: compare get_batch_prices_download vs get_batch_prices_threaded.

Usage:
    uv run python scripts/benchmark_batch_prices.py --size 500 --runs 2
    uv run python scripts/benchmark_batch_prices.py --size 1000 --runs 3
"""

import argparse
import importlib.util
import logging
import pathlib
import random
import resource
import sys
import time

# Load yfinance_client directly to avoid circular imports via __init__.py
_CLIENT_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "app"
    / "services"
    / "market_data"
    / "yfinance_client.py"
)
_spec = importlib.util.spec_from_file_location("yfinance_client", _CLIENT_PATH)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
YFinanceClient = _mod.YFinanceClient
OHLCVRow = _mod.OHLCVRow

SCRIPT_DIR = pathlib.Path(__file__).parent
COOLDOWN_SECONDS = 60

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
)


def load_symbols(size: int) -> list[str]:
    """Load and shuffle test symbols from file."""
    path = SCRIPT_DIR / f"test_symbols_{size}.txt"
    if not path.exists():
        print(f"Error: {path} not found. Run generate_test_symbols.py first.")
        sys.exit(1)
    symbols = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    random.shuffle(symbols)
    return symbols


def get_peak_memory_mb() -> float:
    """Get peak RSS in MB (macOS returns bytes, Linux returns KB)."""
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return usage / (1024 * 1024)
    return usage / 1024


def run_approach(
    client: YFinanceClient,
    symbols: list[str],
    approach: str,
) -> dict:
    """Run one approach and return metrics."""
    mem_before = get_peak_memory_mb()
    start = time.monotonic()

    if approach == "download":
        results = client.get_batch_prices_download(
            symbols, chunk_size=250, chunk_delay=5.0
        )
    else:
        results = client.get_batch_prices_threaded(
            symbols, rate=15.0, max_workers=16
        )

    elapsed = time.monotonic() - start
    mem_after = get_peak_memory_mb()

    successes = {k: v for k, v in results.items() if v is not None}
    failures = {k for k, v in results.items() if v is None}

    return {
        "approach": approach,
        "elapsed": elapsed,
        "success_count": len(successes),
        "failure_count": len(failures),
        "failed_symbols": sorted(failures),
        "results": results,
        "peak_memory_mb": mem_after,
        "memory_delta_mb": mem_after - mem_before,
    }


def compare_results(
    r1: dict[str, OHLCVRow | None],
    r2: dict[str, OHLCVRow | None],
) -> dict:
    """Compare results from two approaches."""
    common_keys = set(r1.keys()) & set(r2.keys())
    both_success = {k for k in common_keys if r1[k] is not None and r2[k] is not None}

    matching = 0
    differing = 0
    diff_details: list[str] = []

    for k in sorted(both_success):
        row1 = r1[k]
        row2 = r2[k]
        if row1 == row2:
            matching += 1
        else:
            differing += 1
            if len(diff_details) < 5:
                diff_details.append(
                    f"  {k}: download.close={row1.close}, threaded.close={row2.close}"
                )

    return {
        "both_success": len(both_success),
        "matching": matching,
        "differing": differing,
        "diff_details": diff_details,
    }


def print_separator() -> None:
    print("-" * 60)


def print_run_result(run_num: int, total_runs: int, metrics: dict) -> None:
    a = metrics["approach"]
    print(
        f"  {a:>12}():  {metrics['elapsed']:6.1f}s "
        f"| {metrics['success_count']:4d} ok "
        f"| {metrics['failure_count']:4d} failed "
        f"| mem={metrics['peak_memory_mb']:.0f}MB"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark batch price fetching")
    parser.add_argument(
        "--size", type=int, choices=[500, 1000], default=500, help="Symbol set size"
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of runs")
    args = parser.parse_args()

    symbols = load_symbols(args.size)
    print(f"Loaded {len(symbols)} symbols")
    print(f"Running {args.runs} run(s)")
    print()

    client = YFinanceClient()
    all_metrics: list[tuple[dict, dict, dict]] = []

    for run in range(1, args.runs + 1):
        # Alternate order to eliminate cache bias
        download_first = run % 2 == 1
        order = ["download", "threaded"] if download_first else ["threaded", "download"]

        random.shuffle(symbols)

        print(f"Run {run}/{args.runs} -- {len(symbols)} symbols (order: {order[0]} first)")
        print_separator()

        first = run_approach(client, symbols, order[0])
        print_run_result(run, args.runs, first)

        if args.runs > 0:
            print(f"  {'':>12}     Cooling down {COOLDOWN_SECONDS}s...")
            time.sleep(COOLDOWN_SECONDS)

        second = run_approach(client, symbols, order[1])
        print_run_result(run, args.runs, second)

        # Compare
        dl = first if first["approach"] == "download" else second
        th = first if first["approach"] == "threaded" else second
        comparison = compare_results(dl["results"], th["results"])

        print(
            f"  {'data match':>12}:   {comparison['matching']}/{comparison['both_success']} identical"
            f" ({comparison['differing']} differ)"
        )
        if comparison["diff_details"]:
            for detail in comparison["diff_details"]:
                print(detail)

        print()
        all_metrics.append((dl, th, comparison))

    # Summary
    if len(all_metrics) > 1:
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)

        dl_times = [m[0]["elapsed"] for m in all_metrics]
        th_times = [m[1]["elapsed"] for m in all_metrics]
        dl_ok = [m[0]["success_count"] for m in all_metrics]
        th_ok = [m[1]["success_count"] for m in all_metrics]

        print(f"  download():  avg {sum(dl_times)/len(dl_times):.1f}s  "
              f"| avg {sum(dl_ok)/len(dl_ok):.0f} ok")
        print(f"  threaded():  avg {sum(th_times)/len(th_times):.1f}s  "
              f"| avg {sum(th_ok)/len(th_ok):.0f} ok")

        ratio = (sum(th_times) / len(th_times)) / (sum(dl_times) / len(dl_times))
        print(f"\n  threaded/download ratio: {ratio:.2f}x")

        if ratio <= 2.0:
            print("  Recommendation: threaded (within 2x, better error handling)")
        else:
            dl_avg = sum(dl_times) / len(dl_times)
            if dl_avg < 900:  # fits in 15 minutes
                print("  Recommendation: download (significantly faster)")
            else:
                print("  WARNING: Neither approach fits in 15-minute window!")


if __name__ == "__main__":
    main()
