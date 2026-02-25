"""
Lucid Clinic — EZBIS EZMERGE.DAT ETL Pipeline
Parses raw EZBIS export, normalizes into clean patient records,
scores each patient for re-engagement priority.
"""

import csv
import json
import sqlite3
import re
from datetime import datetime, date
from pathlib import Path

# ── Column Map (derived from Survey Generator tab screenshots) ──────────────
COL = {
    # General
    "account":          0,
    "type":             1,
    "first_name":       2,
    "middle_initial":   3,
    "last_name":        4,
    "suffix":           5,
    "called_name":      6,
    # date fields 7-11 (various appt/visit dates)
    "last_appt":        12,
    "address":          14,
    "city":             15,
    "state":            16,
    "zip":              17,
    "cell_phone":       18,
    "sex":              20,
    "marital":          21,
    "birthdate":        22,
    "account_date":     23,  # first visit / account created
    "ref_by":           24,
    "appt_reminders":   26,
    "remarks":          27,
    "employment":       29,
    # Insurance (cols 34-73)
    "ins_first":        34,
    "ins_last":         36,
    "ins_address":      37,
    "ins_city":         38,
    "ins_state":        39,
    "ins_zip":          40,
    "ins_phone":        41,
    "ins_policy":       42,
    "ins_dob":          43,
    "ins_sex":          44,
    "ins_rel":          45,
    "ins_carrier":      46,
    "ins_carrier_addr": 48,
    "ins_carrier_city": 49,
    "ins_carrier_phone":51,
    "ins_plan_type":    52,
    "ins_group":        53,
    "ins_member_id":    60,
    "ins_edi":          61,
    "ins_notes":        63,
    "pref_contact":     68,
    "ins_code":         73,
    # Financial (cols 88-108)
    "balance":          88,
    "pat_balance":      89,
    "current":          90,
    "bal_30":           91,
    "bal_60":           92,
    "bal_90":           93,
    "total_charges":    94,
    "total_receipts":   95,
    "total_adjusts":    96,
    "yearly_deduct":    97,
    "copay":            100,
    "pat_percent":      101,
    "visits_allowed":   102,
    "visits_used":      103,  # actually total charges in some rows
    "pay":              104,
    "total_visits":     105,
    "plan_charge":      106,
    "plan_payments":    107,
    # Contact extras
    "alt_phone":        109,
    "work_phone":       110,
    "email":            111,
    "ins_carrier2":     112,
}

def parse_date(s):
    if not s or s.strip() in ('', '00/00/00', '00/00/0000'):
        return None
    s = s.strip()
    for fmt in ('%m/%d/%y', '%m/%d/%Y', '%m/%d/%y'):
        try:
            dt = datetime.strptime(s, fmt)
            # Fix 2-digit year confusion (69+ = 1900s)
            if dt.year > 2030:
                dt = dt.replace(year=dt.year - 100)
            return dt.date().isoformat()
        except:
            pass
    return None

def parse_money(s):
    if not s or not s.strip():
        return 0.0
    try:
        return float(re.sub(r'[^\d.\-]', '', s))
    except:
        return 0.0

def clean_phone(s):
    if not s:
        return None
    # Remove DNC prefix and clean
    s = re.sub(r'^DNC', '', s).strip()
    digits = re.sub(r'\D', '', s)
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return s if s else None

def is_dnc(s):
    return bool(s and s.strip().upper().startswith('DNC'))

def get_col(row, col_name):
    idx = COL.get(col_name)
    if idx is None or idx >= len(row):
        return ''
    return row[idx].strip()

def compute_score(record):
    """
    Re-engagement priority score (0-100).
    Higher = more worth contacting.
    """
    score = 0

    # 1. Recency of last appointment (most important factor)
    last_appt = record.get('last_appt')
    if last_appt:
        try:
            days_ago = (date.today() - date.fromisoformat(last_appt)).days
            if days_ago < 180:      score += 40   # active
            elif days_ago < 365:    score += 35   # warm
            elif days_ago < 730:    score += 28   # cool (1-2 years)
            elif days_ago < 1095:   score += 18   # cold (2-3 years)
            elif days_ago < 1825:   score += 10   # very cold (3-5 years)
            else:                   score += 2    # ancient
        except:
            pass

    # 2. Contact info availability
    if record.get('email'):         score += 20
    if record.get('cell_phone'):    score += 15
    if record.get('alt_phone'):     score += 5

    # 3. Financial value signals
    visits = record.get('total_visits', 0) or 0
    if visits >= 20:                score += 10
    elif visits >= 10:              score += 7
    elif visits >= 5:               score += 4
    elif visits >= 1:               score += 2

    # 4. Has insurance (more likely to return)
    if record.get('ins_carrier'):   score += 8

    # 5. DNC penalty
    if record.get('is_dnc'):        score -= 30

    # 6. No contact info at all
    if not record.get('cell_phone') and not record.get('email') and not record.get('alt_phone'):
        score -= 15

    return max(0, min(100, score))

def classify_tier(score, last_appt):
    if not last_appt:
        return "unknown"
    try:
        days_ago = (date.today() - date.fromisoformat(last_appt)).days
    except:
        return "unknown"

    if days_ago < 180:   return "active"
    if days_ago < 365:   return "warm"
    if days_ago < 730:   return "cool"
    if days_ago < 1825:  return "cold"
    return "dormant"

def parse_row(row):
    raw_cell = get_col(row, 'cell_phone')
    raw_alt  = get_col(row, 'alt_phone')

    record = {
        # Identity
        "account_id":       get_col(row, 'account'),
        "account_type":     get_col(row, 'type'),
        "first_name":       get_col(row, 'first_name').title(),
        "middle_initial":   get_col(row, 'middle_initial'),
        "last_name":        get_col(row, 'last_name').title(),
        "called_name":      get_col(row, 'called_name').title(),
        "suffix":           get_col(row, 'suffix'),
        "sex":              get_col(row, 'sex'),
        "marital":          get_col(row, 'marital'),

        # Dates
        "birthdate":        parse_date(get_col(row, 'birthdate')),
        "last_appt":        parse_date(get_col(row, 'last_appt')),
        "account_created":  parse_date(get_col(row, 'account_date')),

        # Contact
        "address":          get_col(row, 'address').title(),
        "city":             get_col(row, 'city').title(),
        "state":            get_col(row, 'state').upper(),
        "zip":              get_col(row, 'zip'),
        "cell_phone":       clean_phone(raw_cell),
        "alt_phone":        clean_phone(raw_alt),
        "work_phone":       clean_phone(get_col(row, 'work_phone')),
        "email":            get_col(row, 'email').lower() or None,
        "is_dnc":           is_dnc(raw_cell),
        "pref_contact":     get_col(row, 'pref_contact'),
        "appt_reminders":   get_col(row, 'appt_reminders'),

        # Insurance
        "ins_carrier":      get_col(row, 'ins_carrier'),
        "ins_plan_type":    get_col(row, 'ins_plan_type'),
        "ins_group":        get_col(row, 'ins_group'),
        "ins_member_id":    get_col(row, 'ins_member_id'),
        "ins_code":         get_col(row, 'ins_code'),
        "ins_notes":        get_col(row, 'ins_notes'),

        # Financial
        "balance":          parse_money(get_col(row, 'balance')),
        "pat_balance":      parse_money(get_col(row, 'pat_balance')),
        "total_charges":    parse_money(get_col(row, 'total_charges')),
        "total_receipts":   parse_money(get_col(row, 'total_receipts')),
        "total_visits":     None,
        "copay":            parse_money(get_col(row, 'copay')),

        # Meta
        "ref_by":           get_col(row, 'ref_by'),
        "remarks":          get_col(row, 'remarks'),
        "employment":       get_col(row, 'employment'),

        # Scoring (computed below)
        "reengagement_score": 0,
        "tier":             "unknown",
    }

    # Parse total visits carefully
    tv_raw = get_col(row, 'total_visits')
    try:
        record["total_visits"] = int(float(re.sub(r'[^\d.]', '', tv_raw))) if tv_raw else 0
    except:
        record["total_visits"] = 0

    # Fix email
    if record["email"] in ('', 'none', 'n/a'):
        record["email"] = None

    # Score
    record["reengagement_score"] = compute_score(record)
    record["tier"] = classify_tier(record["reengagement_score"], record["last_appt"])

    return record

def build_database(dat_path, db_path):
    print(f"Reading {dat_path}...")
    with open(dat_path, 'r', encoding='latin-1') as f:
        rows = list(csv.reader(f))
    print(f"  → {len(rows)} raw rows, {len(rows[0])} columns each")

    # Deduplicate by account_id (keep last occurrence - most recent data)
    seen = {}
    for row in rows:
        if row:
            seen[row[0]] = row
    rows = list(seen.values())
    print(f"  → {len(rows)} unique accounts after dedup")

    # Parse all rows
    records = []
    errors = 0
    for row in rows:
        try:
            records.append(parse_row(row))
        except Exception as e:
            errors += 1
    print(f"  → {len(records)} parsed, {errors} errors")

    # Build SQLite DB
    print(f"\nBuilding database at {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS patients;
    DROP TABLE IF EXISTS reengagement_queue;

    CREATE TABLE patients (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id          TEXT UNIQUE NOT NULL,
        account_type        TEXT,
        first_name          TEXT,
        middle_initial      TEXT,
        last_name           TEXT,
        called_name         TEXT,
        suffix              TEXT,
        sex                 TEXT,
        marital             TEXT,
        birthdate           TEXT,
        last_appt           TEXT,
        account_created     TEXT,
        address             TEXT,
        city                TEXT,
        state               TEXT,
        zip                 TEXT,
        cell_phone          TEXT,
        alt_phone           TEXT,
        work_phone          TEXT,
        email               TEXT,
        is_dnc              INTEGER DEFAULT 0,
        pref_contact        TEXT,
        appt_reminders      TEXT,
        ins_carrier         TEXT,
        ins_plan_type       TEXT,
        ins_group           TEXT,
        ins_member_id       TEXT,
        ins_code            TEXT,
        ins_notes           TEXT,
        balance             REAL DEFAULT 0,
        pat_balance         REAL DEFAULT 0,
        total_charges       REAL DEFAULT 0,
        total_receipts      REAL DEFAULT 0,
        total_visits        INTEGER DEFAULT 0,
        copay               REAL DEFAULT 0,
        ref_by              TEXT,
        remarks             TEXT,
        employment          TEXT,
        reengagement_score  INTEGER DEFAULT 0,
        tier                TEXT,
        created_at          TEXT DEFAULT (datetime('now')),
        updated_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE reengagement_queue (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id          INTEGER REFERENCES patients(id),
        account_id          TEXT,
        full_name           TEXT,
        called_name         TEXT,
        cell_phone          TEXT,
        email               TEXT,
        last_appt           TEXT,
        days_since_appt     INTEGER,
        tier                TEXT,
        score               INTEGER,
        has_insurance       INTEGER,
        total_visits        INTEGER,
        city                TEXT,
        state               TEXT,
        status              TEXT DEFAULT 'pending',
        created_at          TEXT DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_patients_last_appt ON patients(last_appt);
    CREATE INDEX IF NOT EXISTS idx_patients_tier ON patients(tier);
    CREATE INDEX IF NOT EXISTS idx_patients_score ON patients(reengagement_score DESC);
    CREATE INDEX IF NOT EXISTS idx_patients_email ON patients(email);
    CREATE INDEX IF NOT EXISTS idx_queue_score ON reengagement_queue(score DESC);
    """)

    # Insert patients
    insert_sql = """
    INSERT OR REPLACE INTO patients (
        account_id, account_type, first_name, middle_initial, last_name,
        called_name, suffix, sex, marital, birthdate, last_appt, account_created,
        address, city, state, zip, cell_phone, alt_phone, work_phone, email,
        is_dnc, pref_contact, appt_reminders, ins_carrier, ins_plan_type,
        ins_group, ins_member_id, ins_code, ins_notes,
        balance, pat_balance, total_charges, total_receipts, total_visits, copay,
        ref_by, remarks, employment, reengagement_score, tier
    ) VALUES (
        :account_id, :account_type, :first_name, :middle_initial, :last_name,
        :called_name, :suffix, :sex, :marital, :birthdate, :last_appt, :account_created,
        :address, :city, :state, :zip, :cell_phone, :alt_phone, :work_phone, :email,
        :is_dnc, :pref_contact, :appt_reminders, :ins_carrier, :ins_plan_type,
        :ins_group, :ins_member_id, :ins_code, :ins_notes,
        :balance, :pat_balance, :total_charges, :total_receipts, :total_visits, :copay,
        :ref_by, :remarks, :employment, :reengagement_score, :tier
    )
    """
    conn.executemany(insert_sql, records)

    # Build re-engagement queue (exclude active, DNC, no-contact)
    print("Building re-engagement queue...")
    cur.execute("""
        INSERT INTO reengagement_queue (
            patient_id, account_id, full_name, called_name,
            cell_phone, email, last_appt, days_since_appt,
            tier, score, has_insurance, total_visits, city, state
        )
        SELECT
            p.id,
            p.account_id,
            TRIM(p.first_name || ' ' || p.last_name),
            p.called_name,
            p.cell_phone,
            p.email,
            p.last_appt,
            CAST(julianday('now') - julianday(p.last_appt) AS INTEGER),
            p.tier,
            p.reengagement_score,
            CASE WHEN p.ins_carrier != '' AND p.ins_carrier IS NOT NULL THEN 1 ELSE 0 END,
            p.total_visits,
            p.city,
            p.state
        FROM patients p
        WHERE
            p.tier NOT IN ('active', 'unknown')
            AND p.is_dnc = 0
            AND (p.cell_phone IS NOT NULL OR p.email IS NOT NULL)
            AND p.last_appt IS NOT NULL
            AND p.reengagement_score >= 20
        ORDER BY p.reengagement_score DESC
    """)

    conn.commit()

    # Stats
    stats = {}
    for tier in ['active', 'warm', 'cool', 'cold', 'dormant', 'unknown']:
        cur.execute("SELECT COUNT(*) FROM patients WHERE tier=?", (tier,))
        stats[tier] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM patients WHERE email IS NOT NULL AND email != ''")
    stats['has_email'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM patients WHERE cell_phone IS NOT NULL")
    stats['has_phone'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM patients WHERE is_dnc=1")
    stats['dnc'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM reengagement_queue")
    stats['queue_size'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM patients")
    stats['total'] = cur.fetchone()[0]

    # Top 10 re-engagement candidates
    cur.execute("""
        SELECT full_name, called_name, cell_phone, email, last_appt, days_since_appt, score, tier
        FROM reengagement_queue
        ORDER BY score DESC
        LIMIT 10
    """)
    top10 = cur.fetchall()

    conn.close()
    return stats, top10

if __name__ == "__main__":
    DAT_PATH = "/mnt/user-data/uploads/EZMERGE.DAT"
    DB_PATH  = "/home/claude/pipeline/lucid_clinic.db"

    Path("/home/claude/pipeline").mkdir(exist_ok=True)

    stats, top10 = build_database(DAT_PATH, DB_PATH)

    print("\n" + "="*60)
    print("LUCID CLINIC — DATABASE BUILT SUCCESSFULLY")
    print("="*60)
    print(f"\nTotal patients loaded:     {stats['total']:,}")
    print(f"\nPatient tiers:")
    print(f"  Active  (< 6 months):    {stats['active']:,}")
    print(f"  Warm    (6-12 months):   {stats['warm']:,}")
    print(f"  Cool    (1-2 years):     {stats['cool']:,}")
    print(f"  Cold    (2-5 years):     {stats['cold']:,}")
    print(f"  Dormant (5+ years):      {stats['dormant']:,}")
    print(f"  Unknown:                 {stats['unknown']:,}")
    print(f"\nContact info:")
    print(f"  Has email:               {stats['has_email']:,}")
    print(f"  Has phone:               {stats['has_phone']:,}")
    print(f"  DNC (do not contact):    {stats['dnc']:,}")
    print(f"\nRe-engagement queue:       {stats['queue_size']:,} patients ready")
    print(f"\nTop 10 re-engagement candidates (by score):")
    print(f"{'Name':<25} {'Phone':<18} {'Last Appt':<12} {'Days':<6} {'Score':<6} {'Tier'}")
    print("-"*85)
    for row in top10:
        name, called, phone, email, last_appt, days, score, tier = row
        print(f"{name:<25} {(phone or email or 'N/A'):<18} {(last_appt or 'N/A'):<12} {(days or 0):<6} {score:<6} {tier}")
