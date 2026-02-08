import psycopg2

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres",
    "password": "secret",
    "host": "localhost",
    "port": "5433",
}


def drop_table():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()

        print("Удаляю старую таблицу 'documents'...")

        cur.execute("DROP TABLE IF EXISTS documents CASCADE;")

        print("Успешно! Таблица удалена.")

    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    drop_table()
