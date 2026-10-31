"""Flatten the cached Comtrade JSON in data/raw/ into tidy CSVs in data/.

Values are USD (primaryValue). Output files:
  annual_partners.csv  year, flow, partner_code, partner, value
  annual_hs2.csv       year, flow, hs2, value
  bilateral_hs2.csv    year, flow, partner_code, partner, hs2, value
  monthly.csv          period, flow, partner_code, partner, value
  world_hs2.csv        year, hs2, reporter_code, value
"""
import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
RAW = DATA / "raw"


def rows(prefix):
    for f in sorted(RAW.glob(f"{prefix}*.json")):
        yield from json.loads(f.read_text())["data"] or []


def partner_names():
    # the preview API returns codes only; the reference list maps them to names
    ref = DATA / "ref_partners.json"
    if not ref.exists():
        import subprocess
        url = "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json"
        subprocess.run(["curl", "-sf", "-m", "60", "-o", str(ref), url], check=True)
    return {p["id"]: p["text"] for p in json.loads(ref.read_text())["results"]}


def frame(prefix, cols):
    df = pd.DataFrame(rows(prefix))
    if df.empty:
        return df
    df = df.rename(columns={"refYear": "year", "flowCode": "flow",
                            "partnerCode": "partner_code", "cmdCode": "hs2",
                            "reporterCode": "reporter_code",
                            "primaryValue": "value"})
    # monthly rows carry the month in "period" (YYYYMM)
    return df[cols]


def main():
    names = partner_names()

    def named(df):
        df.insert(df.columns.get_loc("partner_code") + 1, "partner",
                  df["partner_code"].map(names))
        return df

    out = {
        "annual_partners": named(frame("annual_partners_",
                                       ["year", "flow", "partner_code", "value"])),
        "annual_hs2": frame("annual_hs2_", ["year", "flow", "hs2", "value"]),
        "bilateral_hs2": named(frame("bilateral_hs2_",
                                     ["year", "flow", "partner_code", "hs2", "value"])),
        "monthly": named(frame("monthly_", ["period", "flow", "partner_code", "value"])),
        "world_hs2": frame("world_x_", ["year", "hs2", "reporter_code", "value"]),
    }
    for name, df in out.items():
        df.to_csv(DATA / f"{name}.csv", index=False)
        print(f"{name}: {len(df)} rows")


if __name__ == "__main__":
    main()
