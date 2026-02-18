import os

import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer

DB_CONFIG = {
    "dbname": "rag_db",
    "user": "postgres",
    "password": "secretpassword",
    "host": "localhost",
    "port": "5431",
}

DOCS_DIR = "./documents"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIM = 384

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def init_db():
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    print("Сброс таблицы...")
    cur.execute("DROP TABLE IF EXISTS documents;")

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    print(f"Создание таблицы documents (Vector Dim: {VECTOR_DIM})...")
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            filename TEXT,
            content TEXT,
            embedding vector({VECTOR_DIM})
        );
    """)

    try:
        cur.execute(
            "CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);"
        )
    except psycopg2.errors.DuplicateTable:
        pass

    cur.close()
    conn.close()


def recursive_split_text(text, chunk_size, overlap):
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)

        start += chunk_size - overlap

        if start >= text_len:
            break

    return chunks


def process_documents():
    print(f"Загрузка модели {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    conn = get_db_connection()
    cur = conn.cursor()

    if not os.path.exists(DOCS_DIR):
        print(f"Папка {DOCS_DIR} не найдена.")
        return

    files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")]
    total_files = len(files)

    batch_data = []
    BATCH_SIZE = 50

    for idx, filename in enumerate(files):
        file_path = os.path.join(DOCS_DIR, filename)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"Не удалось прочитать {filename}: {e}")
            continue

        chunks = recursive_split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
        if not chunks:
            continue

        embeddings = model.encode(chunks)

        for chunk_text, vector in zip(chunks, embeddings):
            batch_data.append((filename, chunk_text, vector.tolist()))

        if len(batch_data) >= BATCH_SIZE:
            execute_values(
                cur,
                "INSERT INTO documents (filename, content, embedding) VALUES %s",
                batch_data,
            )
            conn.commit()
            print(f"Сохранено {len(batch_data)} чанков...")
            batch_data = []

        print(
            f"[{idx + 1}/{total_files}] Обработан {filename} ({len(chunks)} фрагментов)"
        )

    if batch_data:
        execute_values(
            cur,
            "INSERT INTO documents (filename, content, embedding) VALUES %s",
            batch_data,
        )
        conn.commit()

    cur.close()
    conn.close()
    print("Данные загружены в базу")


if __name__ == "__main__":
    init_db()
    process_documents()
