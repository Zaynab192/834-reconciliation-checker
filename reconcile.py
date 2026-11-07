"""
STEP 3 + 4 + 5: Load both sources into SQL, run the mismatch queries, write the report.
Run:  python reconcile.py
"""
import sqlite3
import re
import pandas as pd
from parse_834 import parse_834, validate_envelope

CENSUS = "data/census.csv"
EDI_FILE = "data/sample_834.edi"

# 1. Load data
census = pd.read_csv(CENSUS)
edi = parse_834(EDI_FILE)

# 2. Put both tables into an in-memory SQLite database
conn = sqlite3.connect(":memory:")
census.to_sql("census", conn, index=False)
edi.to_sql("edi", conn, index=False)

# 3. Read queries.sql and split it into named queries
sql_text = open("queries.sql").read()
parts = re.split(r"-- name: (\w+)", sql_text)      # [junk, name1, sql1, name2, sql2 ...]
queries = dict(zip(parts[1::2], parts[2::2]))

# 4. Run each query, collect results
results = []
for name, sql in queries.items():
    df = pd.read_sql_query(sql, conn)
    df.insert(0, "error_type", name)
    results.append(df)

# 5. Add envelope (file-level) problems
for issue in validate_envelope(EDI_FILE):
    results.append(pd.DataFrame([{"error_type": "envelope_error", "member_id": "FILE",
                                  "name": "", "detail": issue}]))

report = pd.concat(results, ignore_index=True)
report.to_csv("output/error_report.csv", index=False)

# 6. Print a summary
print("=" * 50)
print(f"Census records: {len(census)} | 834 records: {len(edi)}")
print(f"TOTAL ISSUES FOUND: {len(report)}")
print("=" * 50)
print(report.groupby("error_type").size().to_string())
print("\nFull details saved to output/error_report.csv")
