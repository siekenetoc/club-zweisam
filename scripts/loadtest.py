#!/usr/bin/env python3
"""Einfacher Lasttest ohne Zusatzabhängigkeiten.

Beispiel:
  python scripts/loadtest.py --url https://localhost/healthz --requests 300 --concurrency 20
"""
import argparse
import ssl
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def one_request(url: str, timeout: float) -> tuple[bool, float, int]:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=context) as response:
            response.read()
            status = response.status
        return status < 500, time.perf_counter() - started, status
    except Exception:
        return False, time.perf_counter() - started, 0


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(len(ordered) * fraction))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(
            pool.map(
                lambda _: one_request(args.url, args.timeout),
                range(args.requests),
            )
        )
    elapsed = time.perf_counter() - started
    durations = [duration for _, duration, _ in results]
    errors = sum(1 for ok, _, _ in results if not ok)
    statuses: dict[int, int] = {}
    for _, _, status in results:
        statuses[status] = statuses.get(status, 0) + 1

    print(f"URL:          {args.url}")
    print(f"Requests:     {args.requests} (concurrency {args.concurrency})")
    print(f"Duration:     {elapsed:.2f}s")
    print(f"Throughput:   {args.requests / elapsed:.1f} req/s")
    print(f"Errors:       {errors}")
    print(f"Status codes: {statuses}")
    print(f"p50:          {percentile(durations, 0.50) * 1000:.0f} ms")
    print(f"p95:          {percentile(durations, 0.95) * 1000:.0f} ms")
    print(f"p99:          {percentile(durations, 0.99) * 1000:.0f} ms")
    print(f"Mean:         {statistics.mean(durations) * 1000:.0f} ms")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
