"""
Run a scan from the terminal.

    python run.py                                  # default strategy, Yahoo screens
    python run.py --strategy "Oversold Bounce"
    python run.py --tickers AAPL HOOD SOFI         # skip the screens, use your own list
"""
import argparse
import logging
import re

from config.settings import settings
from scan_runner import runner
from strategies.strategy_manager import get_strategy, load_all


DROP_REASONS = [
    (r"^price \$", "price outside the strategy's range"),
    (r"^gap ", "gap under the minimum"),
    (r"^already ran", "ran too far yesterday"),
    (r"^float .* over", "float too large"),
    (r"^float not available", "no float data"),
    (r"^volume .* under", "volume too low"),
    (r"^relative volume", "relative volume too low"),
    (r"^no news", "no news"),
    (r"^negative catalyst", "negative news (offering, lawsuit...)"),
    (r"^no real catalyst", "news doesn't explain the move"),
    (r"^news unavailable", "news api failed"),
    (r"^no .* setup", "no matching setup"),
    (r"too volatile", "stop too wide to size"),
    (r"^outside the top", "watchlist full"),
    (r"^score", "ranked below the final list"),
    (r"^no price history", "no price data from Yahoo"),
]


def summarize_drops(dropped: list[dict]) -> list[tuple[str, int]]:
    """Group drop reasons by rule so 'gap 0.1%' and 'gap 2.2%' count as one reason."""
    counts: dict[str, int] = {}
    for d in dropped:
        label = next((text for pattern, text in DROP_REASONS if re.search(pattern, d["reason"])), d["reason"])
        key = f"{d['agent']}: {label}"
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])


def main():
    parser = argparse.ArgumentParser(description="Stock Radar scan")
    parser.add_argument("--strategy", default=settings.default_strategy)
    parser.add_argument("--tickers", nargs="*")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    strategy = get_strategy(args.strategy)
    if not strategy:
        names = ", ".join(s.name for s in load_all())
        raise SystemExit(f"no strategy named {args.strategy!r}. options: {names}")

    print(f"scanning with {strategy.name} (llm: {settings.llm_model if settings.llm_enabled else 'off'})")
    scan = runner.run_blocking(strategy, args.tickers, trigger="cli")

    if scan["status"] != "done":
        raise SystemExit(f"scan failed: {scan['error']}")

    c = scan["counts"]
    print(f"\n{c['universe']} tickers -> {c['watchlist']} watchlist -> {c['analysis_passed']} with a setup -> {c['final']} final\n")

    for i, cand in enumerate(scan["final"], 1):
        p = cand["plan"]
        print(f"{i:>2}. {cand['ticker']:<6} score {cand['score']:>3}  {cand['setup']:<9} ${cand['price']:<8} "
              f"stop ${p['stop']:<7} target ${p['target_1']:<7} {p['shares']} sh")
        print(f"    {cand['summary']}")

    print("\nwhy tickers were dropped:")
    for reason, count in summarize_drops(scan["dropped"])[:10]:
        print(f"  {count:>4}  {reason}")

    print(f"\nfull results: data/scans/{scan['id']}.json")


if __name__ == "__main__":
    main()
