import os

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),  # Больше никаких секретов в коде!
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": os.getenv("DB_PORT", "5432"),
}


class DBConnector:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = True

    def init_db(self, vector_dim: int):
        with self.conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            query = f"""
            CREATE TABLE IF NOT EXISTS documents (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                metadata JSONB,
                embedding vector({vector_dim})
            );
            """
            cur.execute(query)

            try:
                cur.execute(
                    "CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);"
                )
            except psycopg2.errors.DuplicateTable:
                pass
            print("База данных инициализирована")

    def save_chunk(self, content: str, embedding: list, meta: dict = None):
        if meta is None:
            meta = {}

        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO documents (content, embedding, metadata) VALUES (%s, %s, %s)",
                (content, embedding, Json(meta)),
            )

    def search_similar(self, query_embedding: list, limit: int = 3):
        """Поиск похожих документов по вектору"""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT content, metadata, 1 - (embedding <=> %s::vector) as similarity
                FROM documents
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, limit),
            )
            return cur.fetchall()

            cur.execute(
                """
                SELECT content, metadata, 1 - (embedding <=> %s::vector) as similarity
                FROM documents
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, limit),
            )
            return cur.fetchall()

    def delete_document(self, doc_id: int) -> bool:
        """Удаляет документ по ID. Возвращает True, если удалено успешно."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
            return cur.rowcount > 0
