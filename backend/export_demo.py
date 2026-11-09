"""
Publish the latest scan as the public demo.

    python run.py            # run a real scan first
    python export_demo.py    # copies it to frontend/public/demo-scan.json

Commit and push that file and the demo site redeploys with it.
"""
import json
from pathlib import Path

from utils import scan_store

OUT = Path(__file__).parent.parent / "frontend" / "public" / "demo-scan.json"


def main():
    scan = scan_store.latest()
    if not scan or scan["status"] != "done":
        raise SystemExit("no finished scan yet, run one first: python run.py")
    if not scan["final"]:
        print("heads up: this scan has no picks, so the demo will only show the funnel and drops")

    OUT.write_text(json.dumps(scan, separators=(",", ":"), default=str))
    c = scan["counts"]
    print(f"exported {scan['id']} ({c['universe']} scanned, {c['final']} picks) to {OUT.relative_to(OUT.parent.parent.parent)}")
    print("now: git add frontend/public/demo-scan.json && git commit -m 'update demo scan' && git push")


if __name__ == "__main__":
    main()
