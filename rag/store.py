import chromadb
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
VECTORSTORE_DIR = BASE_DIR / "vectorstore"


class VectorStore:

    def __init__(self):

        VECTORSTORE_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        self.client = chromadb.PersistentClient(
            path=str(VECTORSTORE_DIR)
        )

        self.collection = (
            self.client.get_or_create_collection(
                name="jammer_documents"
            )
        )

    # -------------------------------------------------
    # ADD DOCUMENTS
    # -------------------------------------------------

    def add_documents(
        self,
        chunks,
        embeddings,
        source
    ):

        if not chunks:
            return

        source_path = str(
            Path(source).resolve()
        )

        document_name = Path(source).name

        ids = [
            f"{Path(source).stem}_{i}"
            for i in range(len(chunks))
        ]

        metadatas = [
            {
                "source": source_path,
                "document_name": document_name,
                "chunk_index": i
            }
            for i in range(len(chunks))
        ]

        self.collection.upsert(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

    # -------------------------------------------------
    # SEARCH
    # -------------------------------------------------

    def search(
        self,
        query_embedding,
        n_results=3
    ):

        if self.collection.count() == 0:
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]]
            }

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(
                n_results,
                self.collection.count()
            )
        )

        return results

    # -------------------------------------------------
    # COUNT
    # -------------------------------------------------

    def count(self):

        return self.collection.count()

    # -------------------------------------------------
    # LIST DOCUMENTS
    # -------------------------------------------------

    def list_documents(self):

        if self.collection.count() == 0:
            return []

        results = self.collection.get(
            include=["metadatas"]
        )

        documents = {}

        for metadata in results["metadatas"]:

            source = metadata.get("source")

            if source:
                documents[source] = {
                    "source": source,
                    "document_name": metadata.get(
                        "document_name",
                        Path(source).name
                    )
                }

        return list(documents.values())

    # -------------------------------------------------
    # CLEAR
    # -------------------------------------------------

    def clear(self):

        try:

            self.client.delete_collection(
                name="jammer_documents"
            )

        except Exception:
            pass

        self.collection = (
            self.client.get_or_create_collection(
                name="jammer_documents"
            )
        )