"""
Lucid Clinic — Seed the Supabase Postgres database from all_patients_clean.csv.
Reads the CSV output from etl_pipeline.py and loads it into the database.

Usage:
    python seed.py                          # uses default CSV path
    python seed.py /path/to/patients.csv    # custom CSV path
"""

import csv
import sys
from pathlib import Path
from datetime import date

# Add parent dir so we can import etl helpers
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import engine, Base, SessionLocal
from models import Patient, ReengagementQueue, Campaign, OutreachMessage, AgentSession, Clinic


BATCH_SIZE = 500


def seed_from_csv(csv_path: str):
    print(f"Seeding database from {csv_path}...")

    # Drop and recreate all tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("  Tables created.")

    db = SessionLocal()

    # Load patients in batches for Postgres performance
    patients_batch = []
    total_loaded = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            is_dnc = row.get("is_dnc", "").lower() in ("true", "1", "yes")

            def safe_int(val, default=0):
                try:
                    return int(float(val or default))
                except (ValueError, TypeError):
                    return default

            def safe_float(val, default=0.0):
                try:
                    return float(val or default)
                except (ValueError, TypeError):
                    return default

            email = row.get("email", "").strip() or None
            if email in ("none", "n/a", ""):
                email = None

            p = Patient(
                account_id=row.get("account_id", ""),
                account_type=row.get("account_type", ""),
                first_name=row.get("first_name", ""),
                middle_initial=row.get("middle_initial", ""),
                last_name=row.get("last_name", ""),
                called_name=row.get("called_name", ""),
                suffix=row.get("suffix", ""),
                sex=row.get("sex", ""),
                marital=row.get("marital", ""),
                birthdate=row.get("birthdate", "") or None,
                account_created=row.get("account_created", "") or None,
                last_appt=row.get("last_appt", "") or None,
                address=row.get("address", ""),
                city=row.get("city", ""),
                state=row.get("state", ""),
                zip=row.get("zip", ""),
                cell_phone=row.get("cell_phone", "") or None,
                alt_phone=row.get("alt_phone", "") or None,
                work_phone=row.get("work_phone", "") or None,
                email=email,
                is_dnc=is_dnc,
                pref_contact=row.get("pref_contact", ""),
                ins_carrier=row.get("ins_carrier", ""),
                ins_plan_type=row.get("ins_plan_type", ""),
                ins_group=row.get("ins_group", ""),
                ins_member_id=row.get("ins_member_id", ""),
                ins_code=row.get("ins_code", ""),
                balance=safe_float(row.get("balance")),
                pat_balance=0.0,
                total_charges=safe_float(row.get("total_charges")),
                total_receipts=safe_float(row.get("total_receipts")),
                total_visits=safe_int(row.get("total_visits")),
                copay=safe_float(row.get("copay")),
                ref_by=row.get("ref_by", ""),
                remarks=row.get("remarks", ""),
                employment=row.get("employment", ""),
                reengagement_score=safe_int(row.get("reengagement_score")),
                tier=row.get("tier", "unknown"),
            )
            patients_batch.append(p)

            if len(patients_batch) >= BATCH_SIZE:
                db.add_all(patients_batch)
                db.commit()
                total_loaded += len(patients_batch)
                print(f"  Loaded {total_loaded} patients...")
                patients_batch = []

    # Final batch
    if patients_batch:
        db.add_all(patients_batch)
        db.commit()
        total_loaded += len(patients_batch)

    print(f"  Total: {total_loaded} patients loaded")

    # Build re-engagement queue using raw SQL to avoid connection timeouts
    print("Building re-engagement queue...")
    from sqlalchemy import text
    today = date.today()

    rows = db.execute(text("""
        SELECT id, account_id, first_name, last_name, called_name,
               cell_phone, email, last_appt, tier, reengagement_score,
               ins_carrier, total_visits, city, state
        FROM patients
        WHERE tier NOT IN ('active', 'unknown')
          AND is_dnc = false
          AND last_appt IS NOT NULL
          AND reengagement_score >= 20
          AND (cell_phone IS NOT NULL OR email IS NOT NULL)
        ORDER BY reengagement_score DESC
    """)).fetchall()

    queue_batch = []
    total_queued = 0

    for r in rows:
        days = 0
        if r[7]:  # last_appt
            try:
                days = (today - date.fromisoformat(r[7])).days
            except (ValueError, TypeError):
                pass

        has_ins = bool(r[10] and r[10].strip())  # ins_carrier
        full_name = f"{r[2] or ''} {r[3] or ''}".strip()

        queue_batch.append(ReengagementQueue(
            patient_id=r[0],
            account_id=r[1],
            full_name=full_name,
            called_name=r[4],
            cell_phone=r[5],
            email=r[6],
            last_appt=r[7],
            days_since_appt=days,
            tier=r[8],
            score=r[9],
            has_insurance=has_ins,
            total_visits=r[11],
            city=r[12],
            state=r[13],
            status="pending",
        ))

        if len(queue_batch) >= BATCH_SIZE:
            db.add_all(queue_batch)
            db.commit()
            total_queued += len(queue_batch)
            print(f"  Queued {total_queued} patients...")
            queue_batch = []

    if queue_batch:
        db.add_all(queue_batch)
        db.commit()
        total_queued += len(queue_batch)

    print(f"  Queue built: {total_queued} patients ready for outreach")

    # Stats
    result = db.execute(text("SELECT COUNT(*) FROM patients")).scalar()
    print(f"\nFinal stats ({result} patients):")
    for tier in ["active", "warm", "cool", "cold", "dormant", "unknown"]:
        count = db.execute(text("SELECT COUNT(*) FROM patients WHERE tier = :t"), {"t": tier}).scalar()
        print(f"  {tier}: {count}")

    db.close()
    print("\nDone! Database seeded successfully.")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).resolve().parent.parent / "all_patients_clean.csv"
    )
    seed_from_csv(csv_path)
