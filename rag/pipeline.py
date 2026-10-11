from rag.loader import DocumentLoader
from rag.chunker import TextChunker
from rag.embeddings import LocalEmbeddings
from rag.store import VectorStore
from rag.retriever import Retriever


class RAGPipeline:

    def __init__(self):

        self.loader = DocumentLoader()

        self.chunker = TextChunker(
            chunk_size=800,
            overlap=120
        )

        self.embeddings = LocalEmbeddings()

        self.vector_store = VectorStore()

        self.retriever = Retriever(
            self.vector_store,
            self.embeddings
        )

    # =================================================
    # ADD DOCUMENT
    # =================================================

    def add_document(self, file_path):

        document = self.loader.load(
            file_path
        )

        chunks = self.chunker.split(
            document["text"]
        )

        if not chunks:
            return 0

        embeddings = self.embeddings.embed_documents(
            chunks
        )

        self.vector_store.add_documents(
            chunks=chunks,
            embeddings=embeddings,
            source=document["source"]
        )

        return len(chunks)

    # =================================================
    # SEARCH
    # =================================================

    def search(
    self,
    query,
    n_results=5
):

        return self.retriever.search(
            query,
            n_results
        )

    # =================================================
    # BUILD CONTEXT
    # =================================================

    def build_context(
    self,
    query,
    n_results=5
):

        results = self.search(
            query,
            n_results
        )

        if not results.get("documents"):
            return ""

        documents = results["documents"][0]

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        if not documents:
            return ""

        context_parts = []

        for i, document in enumerate(
            documents
        ):

            source = "Unknown document"

            if i < len(metadatas):

                source = metadatas[i].get(
                    "document_name",
                    "Unknown document"
                )

            context_parts.append(
                f"[Source: {source}]\n"
                f"{document}"
            )

        return "\n\n".join(
            context_parts
        )

        # =================================================
    # GET SOURCES
    # =================================================

    def get_sources(
    self,
    query,
    n_results=5
):
        results = self.search(
            query,
            n_results
        )

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        if not metadatas:
            return []

        sources = []

        for metadata in metadatas:

            source = metadata.get(
                "document_name"
            )

            if source and source not in sources:
                sources.append(source)

        return sources

    # =================================================
    # LIST DOCUMENTS
    # =================================================

    def list_documents(self):

        return self.vector_store.list_documents()

    # =================================================
    # CLEAR DOCUMENTS
    # =================================================

    def clear_documents(self):

        self.vector_store.clear()

    # =================================================
    # DOCUMENT COUNT
    # =================================================

    def document_count(self):

        return len(
            self.vector_store.list_documents()
        )

    # =================================================
    # VECTOR / CHUNK COUNT
    # =================================================

    def chunk_count(self):

        return self.vector_store.count()