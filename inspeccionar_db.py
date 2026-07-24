import sqlite3

conn = sqlite3.connect("data/provicheck.db")

cur = conn.cursor()

print("\n===== TABLAS =====")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
for fila in cur.fetchall():
    print(fila[0])

print("\n===== COLUMNAS =====")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tablas = cur.fetchall()

for (tabla,) in tablas:
    print(f"\n--- {tabla} ---")
    cur.execute(f"PRAGMA table_info({tabla})")
    for c in cur.fetchall():
        print(c[1])

conn.close()