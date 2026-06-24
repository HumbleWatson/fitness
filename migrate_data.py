import json
import sqlite3
import os
import re
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "fitness.db")

NAME_MAP = {
    "引体": "引体向上",
    "二头": "二头弯举",
    "三头": "哑铃臂屈伸",
    "卧推": "哑铃卧推",
    "上斜卧推": "上斜哑铃卧推",
    "下斜卧推": "下斜哑铃卧推",
    "窄距卧推": "窄距哑铃卧推",
    "硬拉": "哑铃硬拉",
    "深蹲": "哑铃高脚杯深蹲",
    "飞鸟": "哑铃飞鸟",
    "前臂": "前臂弯举",
    "推肩": "哑铃推肩",
    "划船": "哑铃划船",
    "臂屈伸": "哑铃臂屈伸",
    "过顶臂屈伸": "哑铃过头臂屈伸",
}

def normalize_exercises(exercises):
    merged = {}
    for ex in exercises:
        raw = ex["name"]
        name = NAME_MAP.get(raw, raw)
        name = re.sub(r'\s+', ' ', name.replace("＆", " & ").replace("&", " & ")).strip()
        if " & " in name:
            for part in name.split(" & "):
                p = part.strip()
                if not p:
                    continue
                merged.setdefault(p, []).extend(dict(s) for s in ex["sets"])
        else:
            merged.setdefault(name, []).extend(dict(s) for s in ex["sets"])
    return [{"name": k, "sets": v} for k, v in merged.items()]


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
