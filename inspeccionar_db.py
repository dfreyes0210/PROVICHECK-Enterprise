import sqlite3

conn = sqlite3.connect("data/provicheck.db")

cur = conn.cursor()

print("COLUMNAS documentos_equipo\n")

cur.execute("PRAGMA table_info(documentos_equipo)")

for c in cur.fetchall():
    print(c)

conn.close()