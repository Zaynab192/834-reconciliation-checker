# 834 Enrollment Reconciliation Checker

When an employee joins, changes plan, or leaves, the employer's data has to reach the insurance carrier as an 834 EDI file. If the two sides disagree, someone can end up uncovered or wrongly covered. This tool finds those mismatches.

## What it does
1. Parses an 834 file into a structured table (Python, pandas)
2. Loads it next to an employer census in SQL (SQLite)
3. Runs mismatch checks and writes an error report

## Checks
- Missing from 834 (active in census, never sent)
- Unexpected in 834 (sent, but not in census)
- DOB mismatch
- Coverage start date mismatch
- Plan mismatch
- Terminated in census but still active in 834
- Duplicate records
- Envelope errors (ISA/IEA, GS/GE, ST/SE control numbers and segment count)

## Results
On synthetic test data (48 members), it caught all 11 planted errors. I then added the plan mismatch check myself and tested it by changing a record.

## How to run
pip install pandas
python generate_data.py
python reconcile.py

Output: output/error_report.csv

## Notes
All data is synthetic, with no real PHI. The 834 format is simplified. Real files vary by carrier companion guide.

## Possible next steps
Carrier-specific rules, CSV and flat-file inputs, a Power BI dashboard of error trends.
