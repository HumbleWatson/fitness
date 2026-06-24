import json
import sqlite3
import os
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "fitness.db")

def normalize_exercises(exercises):
    result = []
    for ex in exercises:
        name = re.sub(r'\s+', ' ', ex["name"].replace("＆", " & ").replace("&", " & ")).strip()
        if name == "引体":
            result.append({**ex, "name": "引体向上"})
        elif " & " in name:
            for part in name.split(" & "):
                p = part.strip()
                if p:
                    result.append({"name": p, "sets": [dict(s) for s in ex["sets"]]})
        else:
            result.append(ex)
    return result


conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT id, date, data FROM records").fetchall()

updated = 0
for row in rows:
    exercises = json.loads(row["data"])
    norm = normalize_exercises(exercises)
    if norm != exercises:
        conn.execute(
            "UPDATE records SET data = ?, updated_at = ? WHERE id = ?",
            (json.dumps(norm), datetime.now().isoformat(), row["id"])
        )
        updated += 1

conn.commit()
conn.close()
print(f"Migrated {updated} records")
