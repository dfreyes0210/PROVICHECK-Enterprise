import os
import sqlite3

print("Ruta actual:")
print(os.getcwd())

print("\n¿Existe data/provicheck.db?")
print(os.path.exists("data/provicheck.db"))

conn = sqlite3.connect("data/provicheck.db")

cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("\nTablas encontradas:")
print(cur.fetchall())

conn.close()