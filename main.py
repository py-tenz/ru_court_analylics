from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import (
    CrossEncoder,
    SentenceTransformer,
)

from core.splitter import QualitativeTextSplitter
from database.connector import DBConnector


class Vectorizer:
    _instance = None
    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def __new__(cls):
        if cls._instance is None:
            print(f"Загрузка Bi-Encoder: {cls.MODEL_NAME}...")
            cls._instance = super(Vectorizer, cls).__new__(cls)
            cls._instance.model = SentenceTransformer(cls.MODEL_NAME)
            print("Bi-Encoder загружен.")
        return cls._instance

    def get_embedding(self, text: str) -> list:
        """Превращает текст в вектор (список float)"""
        embedding = self.model.encode(text)
        return embedding.tolist()

    def get_dimension(self) -> int:
        return self.model.get_sentence_embedding_dimension()


vectorizer = Vectorizer()


app = FastAPI(title="Legal RAG with Reranking")
db = DBConnector()

dim = vectorizer.get_dimension()
db.init_db(dim)

splitter = QualitativeTextSplitter(model_name=vectorizer.MODEL_NAME)

RERANK_MODEL_NAME = "DiTy/cross-encoder-russian-msmarco"
print(f"Загрузка Cross-Encoder (Реранкера): {RERANK_MODEL_NAME}...")
reranker = CrossEncoder(RERANK_MODEL_NAME)
print("Cross-Encoder загружен.")


class DocumentRequest(BaseModel):
    text: str
    metadata: Optional[dict] = {}


class SearchRequest(BaseModel):
    query: str
    limit: int = 3


@app.post("/ingest")
async def ingest_document(doc: DocumentRequest):
    """Загрузка документов в базу"""
    try:
        chunks = splitter.split_text(doc.text)
        saved_count = 0
        for i, chunk in enumerate(chunks):
            vector = vectorizer.get_embedding(chunk)

            chunk_meta = doc.metadata.copy()
            chunk_meta["chunk_index"] = i

            db.save_chunk(chunk, vector, chunk_meta)
            saved_count += 1

        return {"status": "success", "chunks_processed": saved_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
def search_documents(req: SearchRequest):
    """
    Умный поиск:
    1. Векторный поиск находит ТОП-10 кандидатов
    2. Cross-Encoder перепроверяет их и сортирует
    """

    query_vector = vectorizer.get_embedding(req.query)
    candidates = db.search_similar(query_vector, limit=10)

    if not candidates:
        return []
    passage_pairs = [[req.query, doc[0]] for doc in candidates]

    scores = reranker.predict(passage_pairs)

    reranked_results = []
    for i, doc in enumerate(candidates):
        reranked_results.append(
            {
                "content": doc[0],
                "metadata": doc[1],
                "similarity_score": float(scores[i]),
                "old_vector_score": doc[2],
            }
        )

    reranked_results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return reranked_results[: req.limit]


@app.delete("/admin/reset_db")
def reset_database():
    try:
        with db.conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE documents RESTART IDENTITY;")
            db.conn.commit()
        return {"status": "success", "message": "База очищена."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/debug/documents")
def get_all_documents(limit: int = 10):
    """Показывает последние N документов из базы"""
    try:
        with db.conn.cursor() as cur:
            cur.execute(
                "SELECT id, content, embedding, metadata FROM documents ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "content_preview": row[1][:200],
                    "embedding": row[2],
                    "metadata": row[3],
                }
            )
        return results
    except Exception as e:
        return {"error": str(e)}


@app.delete("/documents/{doc_id}")
def delete_document_by_id(doc_id: int):
    """Удаляет конкретный документ из базы по его ID"""
    try:
        is_deleted = db.delete_document(doc_id)

        if is_deleted:
            return {"status": "success", "message": f"Документ {doc_id} удален."}
        else:
            raise HTTPException(
                status_code=404, detail=f"Документ с ID {doc_id} не найден."
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
