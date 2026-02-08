from sentence_transformers import SentenceTransformer


class Vectorizer:
    _instance = None

    MODEL_NAME = "intfloat/multilingual-e5-large"

    def __new__(cls):
        if cls._instance is None:
            print("Загрузка модели BERT")
            cls._instance = super(Vectorizer, cls).__new__(cls)
            cls._instance.model = SentenceTransformer(cls.MODEL_NAME)
            print(f"Модель {cls.MODEL_NAME} загружена")
        return cls._instance

    def get_embedding(self, text: str) -> list:
        """Превращает текст в список чисел (вектор)"""
        embedding = self.model.encode(text)
        return embedding.tolist()

    def get_dimension(self) -> int:
        """Возвращает размерность вектора (нужно для создания таблицы в БД)"""
        return self.model.get_sentence_embedding_dimension()


vectorizer = Vectorizer()
