import sys
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from config import DB_PATH, DATA_DIR

print(f"Config DB_PATH: {DB_PATH}")
db_files = list(DATA_DIR.glob("*.db"))
print(f"Found DB files in {DATA_DIR}: {[f.name for f in db_files]}")

for db_path in db_files:
    print(f"\n==================== {db_path.name} ====================")
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Tables:")
    for t in tables:
        count = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {count} records")

    if "families" in tables:
        print("\n--- FAMILIES ---")
        fams = con.execute("SELECT * FROM families").fetchall()
        for f in fams:
            print(dict(f))

    if "pilgrims" in tables:
        print("\n--- PILGRIMS ---")
        pils = con.execute("SELECT * FROM pilgrims").fetchall()
        for p in pils:
            print(dict(p))

    if "admin_users" in tables:
        print("\n--- ADMIN USERS ---")
        users = con.execute("SELECT id, username, display_name, created_at FROM admin_users").fetchall()
        for u in users:
            print(dict(u))

    con.close()
