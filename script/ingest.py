import csv
import json
import os

from sentence_transformers import SentenceTransformer

DOCS_DIR = "./documents"
OUTPUT_CSV = "vectorized_data.csv"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


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


def process_documents_to_csv():
    print(f"Загрузка модели {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    if not os.path.exists(DOCS_DIR):
        print(f"Папка {DOCS_DIR} не найдена.")
        return

    files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")]
    total_files = len(files)

    with open(OUTPUT_CSV, mode="w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

        writer.writerow(["filename", "content", "embedding"])

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
                vector_str = json.dumps(vector.tolist())

                writer.writerow([filename, chunk_text, vector_str])

            print(
                f"[{idx + 1}/{total_files}] Обработан {filename} ({len(chunks)} фрагментов)"
            )

    print(f"Данные сохранены в файл: {OUTPUT_CSV}")


if __name__ == "__main__":
    process_documents_to_csv()
