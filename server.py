# language: Python, file: server.py
# Zyvix License Server — local test version

from flask import Flask, request, jsonify
import sqlite3
import datetime
import uuid
import sys

app = Flask(__name__)
DB = "licenses.db"

def init_db():
    db = sqlite3.connect(DB)
    db.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            hwid TEXT DEFAULT NULL,
            expires TEXT DEFAULT NULL,
            active INTEGER DEFAULT 1,
            tier TEXT DEFAULT 'basic',
            created TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()
    db.close()

@app.post('/api/verify')
def verify():
    key = request.form.get('key', '').strip()
    hwid = request.form.get('hwid', '').strip()

    if not key or not hwid:
        return jsonify(valid=False, reason="missing_params")

    db = sqlite3.connect(DB)
    cur = db.execute("SELECT hwid, expires, active, tier FROM keys WHERE key=?", (key,))
    row = cur.fetchone()

    if not row:
        db.close()
        print(f"[VERIFY] Invalid key: {key}")
        return jsonify(valid=False, reason="invalid_key")

    stored_hwid, expires, active, tier = row

    if not active:
        db.close()
        print(f"[VERIFY] Disabled key: {key}")
        return jsonify(valid=False, reason="disabled")

    if expires:
        try:
            exp = datetime.datetime.fromisoformat(expires)
            if exp < datetime.datetime.now():
                db.close()
                print(f"[VERIFY] Expired key: {key}")
                return jsonify(valid=False, reason="expired")
        except:
            pass

    if stored_hwid and stored_hwid != hwid:
        db.close()
        print(f"[VERIFY] HWID mismatch: {key} (locked: {stored_hwid[:16]}.. got: {hwid[:16]}..)")
        return jsonify(valid=False, reason="hwid_mismatch")

    if not stored_hwid:
        db.execute("UPDATE keys SET hwid=? WHERE key=?", (hwid, key))
        db.commit()
        print(f"[VERIFY] Locked key {key} to HWID {hwid[:16]}..")

    db.close()
    print(f"[VERIFY] OK: {key} tier={tier}")
    return jsonify(valid=True, tier=tier)

def create_key(tier="basic", duration="month"):
    days = {"day": 1, "week": 7, "month": 30, "lifetime": None}[duration]
    expires = None
    if days:
        expires = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()

    key = "ZYVX-" + uuid.uuid4().hex[:16].upper()
    db = sqlite3.connect(DB)
    db.execute("INSERT INTO keys (key, expires, tier) VALUES (?, ?, ?)", (key, expires, tier))
    db.commit()
    db.close()

    print(f"\n=== KEY GENERATED ===")
    print(f"Key:      {key}")
    print(f"Tier:     {tier}")
    print(f"Duration: {duration} ({expires or 'never'})")
    print(f"=====================\n")
    return key

if __name__ == '__main__':
    init_db()

    if len(sys.argv) > 1 and sys.argv[1] == "genkey":
        tier = sys.argv[2] if len(sys.argv) > 2 else "basic"
        duration = sys.argv[3] if len(sys.argv) > 3 else "month"
        create_key(tier, duration)
    else:
        print("=== Zyvix License Server ===")
        print("Running on http://127.0.0.1:5000")
        print("Generate keys with: python server.py genkey [tier] [day/week/month/lifetime]")
                import os
        port = int(os.environ.get('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
