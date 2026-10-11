from sentence_transformers import SentenceTransformer


class LocalEmbeddings:

    def __init__(
        self,
        model_name="all-MiniLM-L6-v2"
    ):

        print(
            f"Loading embedding model: {model_name}"
        )

        self.model = SentenceTransformer(
            model_name
        )

        print("Embedding model ready.")

    def embed_text(self, text):

        embedding = self.model.encode(
            text,
            normalize_embeddings=True
        )

        return embedding.tolist()

    def embed_documents(self, documents):

        embeddings = self.model.encode(
            documents,
            normalize_embeddings=True
        )

        return embeddings.tolist()