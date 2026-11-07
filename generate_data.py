"""
STEP 1: Make fake data.
Creates two files in the data/ folder:
  1. census.csv     -> what the EMPLOYER says (the "truth")
  2. sample_834.edi -> what RIPPLING sent to the CARRIER (with planted mistakes)
All data is synthetic. No real people. No real PHI.
"""
import csv
import os
import random

random.seed(42)  # same random data every time you run it
os.makedirs("data", exist_ok=True)

FIRST = ["Ravi", "Priya", "Amit", "Neha", "Karan", "Sneha", "Rahul", "Anjali", "Vikram", "Pooja",
         "Arjun", "Meera", "Sanjay", "Divya", "Rohit", "Kavya", "Manish", "Isha", "Nikhil", "Tanvi",
         "Deepak", "Riya", "Suresh", "Nisha", "Varun", "Aditi", "Gaurav", "Simran", "Harsh", "Komal"]
LAST = ["Sharma", "Patel", "Mehta", "Shah", "Iyer", "Khan", "Reddy", "Nair", "Gupta", "Joshi"]
PLANS = ["GOLD PPO", "SILVER HMO", "BRONZE HSA"]


def rand_date(y1, y2):
    """Random date as YYYYMMDD text."""
    return f"{random.randint(y1, y2)}{random.randint(1, 12):02d}{random.randint(1, 28):02d}"


# ---------- build the employer census ----------
members = []
n = 0


def add_member(**kw):
    global n
    n += 1
    kw["member_id"] = f"M{n:04d}"
    members.append(kw)
    return kw


subscribers = []
for i in range(30):
    last = LAST[i % len(LAST)]
    s = add_member(subscriber_id=None, relationship="18", first=FIRST[i], last=last,
                   dob=rand_date(1975, 2000), gender=random.choice("MF"),
                   plan=random.choice(PLANS), start=rand_date(2026, 2026)[:4] + "1201",
                   end="", status="active")
    s["subscriber_id"] = s["member_id"]
    subscribers.append(s)

# first 12 subscribers get dependents
for i in range(12):
    s = subscribers[i]
    add_member(subscriber_id=s["member_id"], relationship="01", first=FIRST[(i + 12) % 30],
               last=s["last"], dob=rand_date(1975, 2000), gender=random.choice("MF"),
               plan=s["plan"], start=s["start"], end="", status="active")
    if i < 6:  # some also get a child
        add_member(subscriber_id=s["member_id"], relationship="19", first=FIRST[(i + 20) % 30],
                   last=s["last"], dob=rand_date(2010, 2022), gender=random.choice("MF"),
                   plan=s["plan"], start=s["start"], end="", status="active")

# 4 subscribers (no dependents) are terminated in the census
for s in subscribers[24:28]:
    s["status"] = "terminated"
    s["end"] = "20261031"

# ---------- write census.csv (dates as YYYY-MM-DD) ----------
def pretty(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if d else ""


with open("data/census.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["member_id", "subscriber_id", "relationship", "first_name", "last_name", "dob",
                "gender", "plan", "coverage_start", "coverage_end", "status"])
    for m in members:
        w.writerow([m["member_id"], m["subscriber_id"], m["relationship"], m["first"], m["last"],
                    pretty(m["dob"]), m["gender"], m["plan"], pretty(m["start"]), pretty(m["end"]),
                    m["status"]])

# ---------- build the 834 (a copy of the census, then PLANT ERRORS) ----------
edi = [dict(m) for m in members]
by_id = {m["member_id"]: m for m in edi}
key = []  # answer key

# Error 1: wrong DOB (two people)
for mid in ["M0003", "M0010"]:
    old = by_id[mid]["dob"]
    by_id[mid]["dob"] = str(int(old[:4]) + 1) + old[4:]
    key.append(f"WRONG DOB: {mid}")

# Error 2: wrong coverage start date (two people)
for mid in ["M0005", "M0016"]:
    by_id[mid]["start"] = by_id[mid]["start"][:4] + "1215"
    key.append(f"WRONG START DATE: {mid}")

# Error 3: missing from the 834 entirely (two people)
missing = ["M0018", "M0019"]
edi = [m for m in edi if m["member_id"] not in missing]
for mid in missing:
    key.append(f"MISSING FROM 834: {mid}")

# Error 4: person in 834 but NOT in census
edi.append(dict(member_id="M9999", subscriber_id="M9999", relationship="18", first="Zoya",
                last="Unknown", dob="19900101", gender="F", plan="GOLD PPO", start="20261201",
                end="", status="active"))
key.append("UNEXPECTED IN 834 (not in census): M9999")

# Error 5: duplicate record
dup = dict(next(m for m in edi if m["member_id"] == "M0020"))
edi.append(dup)
key.append("DUPLICATE IN 834: M0020")

# Error 6: terminated in census, but 834 still says ACTIVE (2 of the 4 terminated)
wrongly_active = [subscribers[26]["member_id"], subscribers[27]["member_id"]]
for mid in wrongly_active:
    by_id[mid]["status"] = "active"      # 834 will send 'add' instead of 'terminate'
    by_id[mid]["end"] = ""
    key.append(f"TERMINATED BUT STILL ACTIVE IN 834: {mid}")

# ---------- write the 834 file ----------
segs = []
for m in edi:
    is_sub = "Y" if m["relationship"] == "18" else "N"
    terminated = m["status"] == "terminated"
    action = "024" if terminated else "021"
    reason = "07" if terminated else "28"
    segs.append(f"INS*{is_sub}*{m['relationship']}*{action}*{reason}*A***FT")
    segs.append(f"REF*0F*{m['subscriber_id']}")
    segs.append("REF*1L*GRP5555")
    segs.append(f"NM1*IL*1*{m['last'].upper()}*{m['first'].upper()}****MI*{m['member_id']}")
    segs.append(f"DMG*D8*{m['dob']}*{m['gender']}")
    segs.append(f"HD*{action}**HLT*{m['plan']}*FAM")
    segs.append(f"DTP*348*D8*{m['start']}")
    if terminated:
        segs.append(f"DTP*349*D8*{m['end']}")

header = ["ST*834*0001*005010X220A1", "BGN*00*12345*20261105*093000****2",
          "N1*P5*ACME CORP*FI*123456789", "N1*IN*SAMPLE HEALTH*FI*987654321"]
real_se_count = len(header) + len(segs) + 1       # ST..SE inclusive
PLANT_BAD_SE = True
se_count = real_se_count - 2 if PLANT_BAD_SE else real_se_count
if PLANT_BAD_SE:
    key.append(f"ENVELOPE: SE says {se_count} segments but real count is {real_se_count}")

isa = ("ISA*00*          *00*          *ZZ*RIPPLINGTEST   *ZZ*CARRIERTEST    "
       "*261105*0930*^*00501*000000101*0*T*:")
gs = "GS*BE*RIPPLINGTEST*CARRIERTEST*20261105*0930*101*X*005010X220A1"
all_segs = [isa, gs] + header + segs + [f"SE*{se_count}*0001", "GE*1*101", "IEA*1*000000101"]

with open("data/sample_834.edi", "w") as f:
    f.write("~\n".join(all_segs) + "~\n")

with open("data/answer_key.txt", "w") as f:
    f.write("PLANTED ERRORS (don't peek until your tool has run!)\n")
    f.write("\n".join(key) + "\n")

print(f"Census members: {len(members)}")
print(f"834 member records: {len(edi)}")
print(f"Planted {len(key)} errors. Answer key saved to data/answer_key.txt")
