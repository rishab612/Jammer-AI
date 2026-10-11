class Retriever:

    def __init__(
        self,
        vector_store,
        embeddings
    ):
        self.vector_store = vector_store
        self.embeddings = embeddings

    def search(
        self,
        query,
        n_results=5,
        min_distance=1.45,
        max_results=2
    ):
        query_embedding = self.embeddings.embed_text(query)

        results = self.vector_store.search(
            query_embedding,
            n_results
        )

        if not results.get("documents"):
            return results

        documents = results["documents"][0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        filtered = []

        for index, document in enumerate(documents):

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            if distance is not None and distance <= min_distance:

                metadata = (
                    metadatas[index]
                    if index < len(metadatas)
                    else {}
                )

                filtered.append({
                    "document": document,
                    "metadata": metadata,
                    "distance": distance
                })

        # Chroma already returns results ordered
        # from most similar to least similar.
        filtered = filtered[:max_results]

        return {
            "documents": [[item["document"] for item in filtered]],
            "metadatas": [[item["metadata"] for item in filtered]],
            "distances": [[item["distance"] for item in filtered]]
        }