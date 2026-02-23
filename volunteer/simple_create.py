import os
import sys

# Перевіряємо, чи існує база даних
db_path = '/home/ruslan-pertsovych/Desktop/Diploma/volunteer/db.sqlite3'
if not os.path.exists(db_path):
    print("База даних не існує. Спочатку запустіть міграції.")
    sys.exit(1)

print("База даних існує. Перевіряємо, чи є користувачі...")

# Проста перевірка через sqlite3
import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Перевіряємо, чи є користувачі
cursor.execute("SELECT COUNT(*) FROM volunteer_app_user")
user_count = cursor.fetchone()[0]
print(f"Кількість користувачів: {user_count}")

# Перевіряємо, чи є проекти
cursor.execute("SELECT COUNT(*) FROM volunteer_app_projects")
project_count = cursor.fetchone()[0]
print(f"Кількість проектів: {project_count}")

# Перевіряємо, чи є завдання
cursor.execute("SELECT COUNT(*) FROM volunteer_app_task")
task_count = cursor.fetchone()[0]
print(f"Кількість завдань: {task_count}")

conn.close()

if user_count == 0:
    print("⚠️  Користувачів немає! Потрібно створити користувачів.")
elif project_count == 0:
    print("⚠️  Проектів немає! Потрібно створити проекти.")
else:
    print("✅ Дані існують, можна тестувати.")
