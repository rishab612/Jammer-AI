from rag.loader import DocumentLoader
from rag.chunker import TextChunker
from rag.embeddings import LocalEmbeddings
from rag.store import VectorStore


FILE_PATH = "rag/documents/test.txt"


print("Loading document...")

loader = DocumentLoader()

document = loader.load(
    FILE_PATH
)

print(
    f"Loaded: {document['source']}"
)


print("\nChunking document...")

chunker = TextChunker(
    chunk_size=300,
    overlap=50
)

chunks = chunker.split(
    document["text"]
)

print(
    f"Created {len(chunks)} chunks."
)


print("\nCreating embeddings...")

embedding_model = LocalEmbeddings()

embeddings = embedding_model.embed_documents(
    chunks
)

print(
    f"Created {len(embeddings)} embeddings."
)


print("\nStoring vectors...")

vector_store = VectorStore()

vector_store.add_documents(
    chunks=chunks,
    embeddings=embeddings,
    source=document["source"]
)

print(
    f"Vector database contains "
    f"{vector_store.count()} chunks."
)


print("\nTesting semantic search...")

query = "What graphics card does Jammer's computer use?"

query_embedding = embedding_model.embed_text(
    query
)

results = vector_store.search(
    query_embedding,
    n_results=3
)


print("\nSEARCH RESULTS")
print("=" * 60)

for i, document in enumerate(
    results["documents"][0]
):

    print(f"\nResult {i + 1}:")
    print(document)

print("\nDone.")