import re
import pandas as pd
from io import StringIO

html = open("out/report.html", encoding="utf-8").read()
print("size KB:", round(len(html) / 1024, 1))
print("details sections:", html.lower().count("<details"))

tables = pd.read_html(StringIO(html))
print("tables found:", len(tables))

weekly_total = 0
weekly_n = 0
for t in tables:
    cols = [str(c).lower() for c in t.columns]
    if "breaches" in cols:
        b = pd.to_numeric(t[t.columns[cols.index("breaches")]], errors="coerce").sum()
        first = str(t.columns[0])
        print(f"table cols={list(t.columns)[:4]}... rows={len(t)} breaches_sum={int(b)}")
        if "week" not in first.lower():
            continue
        weekly_total += b
        weekly_n += 1

print("weekly agent tables:", weekly_n, "| their breaches sum:", int(weekly_total))