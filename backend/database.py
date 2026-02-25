"""Lucid Clinic — Database connection and session management (Supabase Postgres)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool, NullPool

from config import DATABASE_URL

# Clean up url because users sometimes copy with quotes or spaces
db_url = DATABASE_URL.strip().strip('"').strip("'")

# SQLAlchemy 2.0+ requires postgresql:// instead of postgres://
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

# If connecting to a Supabase transaction pooler (port 6543), QueuePool causes issues.
# Use NullPool instead so the DB handles pooling.
pool_class = NullPool if "6543" in db_url else QueuePool

engine = create_engine(
    db_url if db_url else "sqlite:///:memory:", # Fallback to prevent crash on boot
    poolclass=pool_class,
    pool_pre_ping=True,
    **(
        {} if pool_class == NullPool else {"pool_size": 5, "max_overflow": 10, "pool_recycle": 300}
    )
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
