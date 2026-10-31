"""Download Japan trade data from the UN Comtrade public preview API.

Every response is cached as raw JSON in data/raw/, so a rerun only fetches
what is missing. With a subscription key in ~/.comtrade_key (never committed)
the keyed endpoint is used: up to 12 periods and 100,000 rows per call.
Without one, the public preview: no key, one period per call, 500 rows,
and an hourly call quota.

Usage: python3 fetch_comtrade.py [annual|hs2|bilateral|monthly|world|all]
"""
import json
import re
import sys
import subprocess
import time
from pathlib import Path

KEY_FILE = Path.home() / ".comtrade_key"
KEY = KEY_FILE.read_text().strip() if KEY_FILE.exists() else None
BASE = ("https://comtradeapi.un.org/data/v1/get/C" if KEY
        else "https://comtradeapi.un.org/public/v1/preview/C")
CAP = 100_000 if KEY else 500
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
JAPAN = 392
YEARS = range(2000, 2025)          # annual 2025 not yet published (checked 2026-10-30)
SNAPSHOT_YEARS = (2005, 2015, 2024)
RCA_YEARS = (2005, 2024)

# Key partners: US, China, Korea, Taiwan ("Other Asia, nes" = 490), Hong Kong,
# Thailand, Vietnam, Malaysia, Indonesia, Philippines, Singapore, India,
# Germany, Australia, Saudi Arabia, UAE
PARTNERS = [842, 156, 410, 490, 344, 764, 704, 458, 360, 608, 702, 699,
            276, 36, 682, 784]
MONTHLY_PARTNERS = [0, 842, 156, 410, 490, 682, 784]
HS2 = [f"{i:02d}" for i in range(1, 98) if i != 77]


def get(name, freq, **params):
    path = RAW / f"{name}.json"
    if path.exists():
        return
    # totals only: no customs-procedure / transport-mode / 2nd-partner splits
    params = {"customsCode": "C00", "motCode": 0, "partner2Code": 0, **params}
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE}/{freq}/HS?{query}"
    attempt = 0
    while attempt < 5:
        try:
            # curl, not urllib: this Python has no CA certificates installed
            cmd = ["curl", "-s", "-m", "300", url]
            if KEY:
                cmd += ["-H", f"Ocp-Apim-Subscription-Key: {KEY}"]
            out = subprocess.run(cmd,
                                 capture_output=True, check=True).stdout
            body = json.loads(out)
            # anonymous quota: 403 "Out of call volume quota. Quota will be
            # replenished in HH:MM:SS." -- wait it out, don't count as a retry
            m = re.search(r"replenished in (\d+):(\d+):(\d+)",
                          body.get("message") or "")
            if m:
                h, mi, s = map(int, m.groups())
                wait = h * 3600 + mi * 60 + s + 10
                print(f"quota {name}: waiting {wait}s", flush=True)
                time.sleep(wait)
                continue
            if body.get("statusCode", 200) >= 400:
                raise RuntimeError(body.get("message"))
            if body.get("error"):
                raise RuntimeError(body["error"])
            rows = body.get("data") or []
            if len(rows) >= CAP:
                print(f"WARNING {name}: hit {CAP}-row cap", flush=True)
            path.write_text(json.dumps(body, ensure_ascii=False))
            print(f"ok {name}: {len(rows)} rows", flush=True)
            time.sleep(1.5)
            return
        except Exception as e:
            attempt += 1
            wait = 5 * attempt
            print(f"retry {name} ({e}); sleeping {wait}s", flush=True)
            time.sleep(wait)
    print(f"FAILED {name}", flush=True)


def annual():
    # totals + every partner, exports and imports
    for y in YEARS:
        get(f"annual_partners_{y}", "A", reporterCode=JAPAN, flowCode="X,M",
            period=y, cmdCode="TOTAL")


def hs2():
    # commodity structure vs the world
    for y in YEARS:
        get(f"annual_hs2_{y}", "A", reporterCode=JAPAN, flowCode="X,M",
            period=y, partnerCode=0, cmdCode="AG2")


def bilateral():
    # commodity x partner, two partners per call to stay under 500 rows
    for y in SNAPSHOT_YEARS:
        for i in range(0, len(PARTNERS), 2):
            pair = PARTNERS[i:i + 2]
            get(f"bilateral_hs2_{y}_{'-'.join(map(str, pair))}", "A",
                reporterCode=JAPAN, flowCode="X,M", period=y,
                partnerCode=",".join(map(str, pair)), cmdCode="AG2")


def monthly():
    partners = ",".join(map(str, MONTHLY_PARTNERS))
    if KEY:
        # one call per year; drops month files of that year left by the preview
        for y in range(2010, 2026):
            months = [RAW / f"monthly_{y}{m:02d}.json" for m in range(1, 13)]
            if all(f.exists() for f in months):
                continue
            get(f"monthly_{y}", "M", reporterCode=JAPAN, flowCode="X,M",
                period=",".join(f"{y}{m:02d}" for m in range(1, 13)),
                partnerCode=partners, cmdCode="TOTAL")
            if (RAW / f"monthly_{y}.json").exists():
                for f in months:
                    f.unlink(missing_ok=True)
        return
    for y in range(2010, 2026):
        for m in range(1, 13):
            if (y, m) > (2025, 12):
                break
            get(f"monthly_{y}{m:02d}", "M", reporterCode=JAPAN,
                flowCode="X,M", period=f"{y}{m:02d}",
                partnerCode=partners, cmdCode="TOTAL")


def world():
    # all reporters' exports per HS chapter, for the Balassa RCA denominator
    for y in RCA_YEARS:
        if KEY:
            get(f"world_x_{y}", "A", flowCode="X", period=y, partnerCode=0,
                cmdCode="AG2")
            continue
        for ch in HS2:
            get(f"world_x_{y}_{ch}", "A", flowCode="X", period=y,
                partnerCode=0, cmdCode=ch)


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    jobs = {"annual": annual, "hs2": hs2, "bilateral": bilateral,
            "monthly": monthly, "world": world}
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, job in jobs.items():
        if which in (name, "all"):
            job()
