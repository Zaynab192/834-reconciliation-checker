"""
STEP 2: Read the 834 file and turn it into a table.
Rules of the 834 format:
  - '~' ends a segment (one line of the form)
  - '*' separates the fields inside a segment
Run on its own to test:  python parse_834.py
"""
import pandas as pd


def read_segments(path):
    """Open the file and return a list of segments. Each segment = list of fields."""
    with open(path) as f:
        text = f.read().replace("\n", "")      # file may be split across lines, remove that
    raw_segments = [s for s in text.split("~") if s.strip()]
    return [s.split("*") for s in raw_segments]   # 'INS*Y*18' -> ['INS','Y','18']


def to_iso(d8):
    """Turn 20261201 into 2026-12-01."""
    return f"{d8[:4]}-{d8[4:6]}-{d8[6:]}" if d8 else None


def parse_834(path):
    """Return a table with one row per member record in the 834."""
    members = []
    current = None

    for seg in read_segments(path):
        tag = seg[0]                        # first field = segment name

        if tag == "INS":                    # a new member starts here
            current = {
                "is_subscriber": seg[1],    # Y = employee, N = dependent
                "relationship": seg[2],     # 18 self, 01 spouse, 19 child
                "action": seg[3],           # 021 add, 024 terminate
                "coverage_end": None,
            }
            members.append(current)
        elif current is None:
            continue                        # ignore header segments before first INS
        elif tag == "REF" and seg[1] == "0F":
            current["subscriber_id"] = seg[2]
        elif tag == "NM1" and seg[1] == "IL":
            current["last_name"] = seg[3]
            current["first_name"] = seg[4]
            current["member_id"] = seg[9]
        elif tag == "DMG":
            current["dob"] = to_iso(seg[2])
            current["gender"] = seg[3]
        elif tag == "HD":
            current["plan"] = seg[4]
        elif tag == "DTP" and seg[1] == "348":     # coverage start
            current["coverage_start"] = to_iso(seg[3])
        elif tag == "DTP" and seg[1] == "349":     # coverage end
            current["coverage_end"] = to_iso(seg[3])

    return pd.DataFrame(members)


def validate_envelope(path):
    """Check the 'wrapping paper': control numbers match and segment count is right."""
    segs = read_segments(path)
    issues = []
    find = lambda tag: next((s for s in segs if s[0] == tag), None)

    isa, iea = find("ISA"), find("IEA")
    gs, ge = find("GS"), find("GE")
    st, se = find("ST"), find("SE")

    if isa[13] != iea[2]:
        issues.append(f"ISA control number {isa[13]} does not match IEA {iea[2]}")
    if gs[6] != ge[2]:
        issues.append(f"GS control number {gs[6]} does not match GE {ge[2]}")
    if st[2] != se[2]:
        issues.append(f"ST control number {st[2]} does not match SE {se[2]}")

    # SE01 must equal the number of segments from ST to SE (inclusive)
    st_pos = segs.index(st)
    se_pos = segs.index(se)
    real_count = se_pos - st_pos + 1
    if int(se[1]) != real_count:
        issues.append(f"SE says {se[1]} segments, but the file really has {real_count}")
    return issues


if __name__ == "__main__":
    df = parse_834("data/sample_834.edi")
    print(df.head(10).to_string())
    print(f"\nTotal member records: {len(df)}")
    print("Envelope issues:", validate_envelope("data/sample_834.edi") or "none")
