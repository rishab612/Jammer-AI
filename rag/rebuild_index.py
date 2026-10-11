from pathlib import Path

from rag.loader import DocumentLoader
from rag.chunker import TextChunker
from rag.embeddings import LocalEmbeddings
from rag.store import VectorStore


DOCUMENTS_DIR = Path("rag/documents")


def main():

    print("=" * 60)
    print("           JAMMER RAG INDEX REBUILD")
    print("=" * 60)
    print()

    # -------------------------------------------------
    # INITIALIZE COMPONENTS
    # -------------------------------------------------

    loader = DocumentLoader()

    chunker = TextChunker(
        chunk_size=800,
        overlap=120,
        min_chunk_size=100
    )

    embeddings = LocalEmbeddings()

    vector_store = VectorStore()

    # -------------------------------------------------
    # CLEAR OLD INDEX
    # -------------------------------------------------

    print("Clearing existing vector index...")

    vector_store.clear()

    print("Old index cleared.")
    print()

    # -------------------------------------------------
    # FIND DOCUMENTS
    # -------------------------------------------------

    files = [
        file
        for file in DOCUMENTS_DIR.iterdir()
        if file.is_file()
        and file.suffix.lower()
        in DocumentLoader.SUPPORTED_EXTENSIONS
    ]

    if not files:

        print("No supported documents found.")

        return

    print(
        f"Found {len(files)} document(s)."
    )

    print()

    # -------------------------------------------------
    # PROCESS DOCUMENTS
    # -------------------------------------------------

    total_chunks = 0

    for file_path in files:

        print(
            f"Processing: {file_path.name}"
        )

        try:

            document = loader.load(
                file_path
            )

            chunks = chunker.split(
                document["text"]
            )

            if not chunks:

                print(
                    "  No readable text found."
                )

                print()

                continue

            print(
                f"  Chunks: {len(chunks)}"
            )

            document_embeddings = (
                embeddings.embed_documents(
                    chunks
                )
            )

            vector_store.add_documents(
                chunks=chunks,
                embeddings=document_embeddings,
                source=document["source"]
            )

            total_chunks += len(chunks)

            print(
                "  Indexed successfully."
            )

        except Exception as error:

            print(
                f"  Failed: {error}"
            )

        print()

    # -------------------------------------------------
    # SUMMARY
    # -------------------------------------------------

    print("=" * 60)
    print("REBUILD COMPLETE")
    print("=" * 60)

    print(
        f"Documents indexed : {len(files)}"
    )

    print(
        f"Chunks indexed     : {total_chunks}"
    )

    print(
        f"Database chunks    : {vector_store.count()}"
    )

    print()


if __name__ == "__main__":

    main()