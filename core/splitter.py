from typing import List

from sentence_transformers import SentenceTransformer


class QualitativeTextSplitter:
    def __init__(self, model_name: str, max_tokens: int = 256, overlap: int = 30):
        self.model = SentenceTransformer(model_name)
        self.max_tokens = max_tokens
        self.overlap = overlap

    def split_text(self, text: str) -> List[str]:
        raw_sentences = text.replace("!", ".").replace("?", ".").split(".")
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            token_count = len(self.model.tokenizer.encode(sentence))

            if current_length + token_count > self.max_tokens:
                full_chunk_text = ". ".join(current_chunk) + "."
                chunks.append(full_chunk_text)

                overlap_sentences = current_chunk[-1:] if current_chunk else []
                current_chunk = overlap_sentences + [sentence]

                current_length = len(
                    self.model.tokenizer.encode(". ".join(current_chunk))
                )
            else:
                current_chunk.append(sentence)
                current_length += token_count

        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")

        return chunks
