import unittest
from unittest.mock import MagicMock, patch

from rag.pipeline import RAGPipeline
from rag.retriever import Retriever


class TestRAGPipeline(unittest.TestCase):

    def setUp(self):
        self.patches = [
            patch("rag.pipeline.DocumentLoader"),
            patch("rag.pipeline.TextChunker"),
            patch("rag.pipeline.LocalEmbeddings"),
            patch("rag.pipeline.VectorStore"),
            patch("rag.pipeline.Retriever"),
        ]

        self.mocks = [p.start() for p in self.patches]
        self.addCleanup(self.stop_patches)

        (
            self.loader_cls,
            self.chunker_cls,
            self.embeddings_cls,
            self.store_cls,
            self.retriever_cls,
        ) = self.mocks

        self.pipeline = RAGPipeline()

        self.loader = self.pipeline.loader
        self.chunker = self.pipeline.chunker
        self.embeddings = self.pipeline.embeddings
        self.store = self.pipeline.vector_store
        self.retriever = self.pipeline.retriever

    def stop_patches(self):
        for patcher in reversed(self.patches):
            patcher.stop()

    def test_add_document_stores_chunks_and_embeddings(self):
        self.loader.load.return_value = {
            "text": "Document content",
            "source": "sample.txt",
        }
        self.chunker.split.return_value = ["chunk one", "chunk two"]
        self.embeddings.embed_documents.return_value = [
            [0.1, 0.2],
            [0.3, 0.4],
        ]

        count = self.pipeline.add_document("sample.txt")

        self.assertEqual(count, 2)
        self.loader.load.assert_called_once_with("sample.txt")
        self.chunker.split.assert_called_once_with("Document content")
        self.embeddings.embed_documents.assert_called_once_with(
            ["chunk one", "chunk two"]
        )
        self.store.add_documents.assert_called_once_with(
            chunks=["chunk one", "chunk two"],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            source="sample.txt",
        )

    def test_add_document_returns_zero_for_empty_chunks(self):
        self.loader.load.return_value = {
            "text": "",
            "source": "empty.txt",
        }
        self.chunker.split.return_value = []

        count = self.pipeline.add_document("empty.txt")

        self.assertEqual(count, 0)
        self.embeddings.embed_documents.assert_not_called()
        self.store.add_documents.assert_not_called()

    def test_search_delegates_to_retriever(self):
        expected = {
            "documents": [["Relevant text"]],
            "metadatas": [[{"document_name": "notes.txt"}]],
            "distances": [[0.2]],
        }
        self.retriever.search.return_value = expected

        result = self.pipeline.search("test query", n_results=3)

        self.assertEqual(result, expected)
        self.retriever.search.assert_called_once_with("test query", 3)

    def test_search_uses_default_result_count(self):
        self.pipeline.search("test query")

        self.retriever.search.assert_called_once_with("test query", 5)

    def test_build_context_formats_sources_and_documents(self):
        self.pipeline.search = MagicMock(return_value={
            "documents": [["First passage", "Second passage"]],
            "metadatas": [
                [
                    {"document_name": "first.txt"},
                    {"document_name": "second.pdf"},
                ]
            ],
        })

        context = self.pipeline.build_context("query")

        self.assertIn("[Source: first.txt]", context)
        self.assertIn("First passage", context)
        self.assertIn("[Source: second.pdf]", context)
        self.assertIn("Second passage", context)

    def test_build_context_uses_unknown_source_when_metadata_missing(self):
        self.pipeline.search = MagicMock(return_value={
            "documents": [["Some content"]],
        })

        context = self.pipeline.build_context("query")

        self.assertIn("[Source: Unknown document]", context)
        self.assertIn("Some content", context)

    def test_build_context_returns_empty_string_without_documents(self):
        self.pipeline.search = MagicMock(return_value={
            "documents": [[]],
            "metadatas": [[]],
        })

        self.assertEqual(self.pipeline.build_context("query"), "")

    def test_build_context_handles_missing_documents_key(self):
        self.pipeline.search = MagicMock(return_value={})

        self.assertEqual(self.pipeline.build_context("query"), "")

    def test_get_sources_returns_unique_document_names(self):
        self.pipeline.search = MagicMock(return_value={
            "metadatas": [[
                {"document_name": "resume.pdf"},
                {"document_name": "notes.txt"},
                {"document_name": "resume.pdf"},
                {},
            ]]
        })

        sources = self.pipeline.get_sources("query")

        self.assertEqual(sources, ["resume.pdf", "notes.txt"])

    def test_get_sources_returns_empty_list_without_metadata(self):
        self.pipeline.search = MagicMock(return_value={
            "documents": [[]],
            "metadatas": [[]],
        })

        self.assertEqual(self.pipeline.get_sources("query"), [])

    def test_list_documents_delegates_to_store(self):
        expected = [{"source": "a.txt", "document_name": "a.txt"}]
        self.store.list_documents.return_value = expected

        self.assertEqual(self.pipeline.list_documents(), expected)

    def test_clear_documents_delegates_to_store(self):
        self.pipeline.clear_documents()

        self.store.clear.assert_called_once_with()

    def test_document_count_counts_unique_documents(self):
        self.store.list_documents.return_value = [
            {"source": "a.txt"},
            {"source": "b.pdf"},
        ]

        self.assertEqual(self.pipeline.document_count(), 2)

    def test_chunk_count_delegates_to_store(self):
        self.store.count.return_value = 7

        self.assertEqual(self.pipeline.chunk_count(), 7)


class TestRetriever(unittest.TestCase):

    def setUp(self):
        self.store = MagicMock()
        self.embeddings = MagicMock()
        self.embeddings.embed_text.return_value = [0.1, 0.2]
        self.retriever = Retriever(self.store, self.embeddings)

    def test_search_filters_by_distance_and_limits_results(self):
        self.store.search.return_value = {
            "documents": [[
                "Closest passage",
                "Second passage",
                "Too distant passage",
                "Fourth passage",
            ]],
            "metadatas": [[
                {"document_name": "a.txt"},
                {"document_name": "b.txt"},
                {"document_name": "c.txt"},
                {"document_name": "d.txt"},
            ]],
            "distances": [[0.1, 0.5, 1.8, 0.7]],
        }

        result = self.retriever.search("query")

        self.assertEqual(
            result["documents"],
            [["Closest passage", "Second passage"]],
        )
        self.assertEqual(
            result["metadatas"],
            [[
                {"document_name": "a.txt"},
                {"document_name": "b.txt"},
            ]],
        )
        self.assertEqual(result["distances"], [[0.1, 0.5]])

    def test_search_uses_embedding_and_passes_result_count(self):
        self.store.search.return_value = {
            "documents": [["Relevant passage"]],
            "metadatas": [[{"document_name": "a.txt"}]],
            "distances": [[0.2]],
        }

        self.retriever.search("hello", n_results=3)

        self.embeddings.embed_text.assert_called_once_with("hello")
        self.store.search.assert_called_once_with([0.1, 0.2], 3)

    def test_search_respects_custom_distance_threshold(self):
        self.store.search.return_value = {
            "documents": [["Passage A", "Passage B"]],
            "metadatas": [[{}, {}]],
            "distances": [[0.4, 0.8]],
        }

        result = self.retriever.search(
            "query",
            min_distance=0.5,
            max_results=5,
        )

        self.assertEqual(result["documents"], [["Passage A"]])
        self.assertEqual(result["distances"], [[0.4]])

    def test_search_respects_custom_max_results(self):
        self.store.search.return_value = {
            "documents": [["A", "B", "C"]],
            "metadatas": [[{}, {}, {}]],
            "distances": [[0.1, 0.2, 0.3]],
        }

        result = self.retriever.search(
            "query",
            max_results=1,
        )

        self.assertEqual(result["documents"], [["A"]])

    def test_search_returns_empty_store_results(self):
        empty_result = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        self.store.search.return_value = empty_result

        result = self.retriever.search("query")

        self.assertEqual(result, empty_result)

    def test_search_excludes_results_without_distance(self):
        self.store.search.return_value = {
            "documents": [["Passage A", "Passage B"]],
            "metadatas": [[{}, {}]],
            "distances": [[0.1]],
        }

        result = self.retriever.search("query")

        self.assertEqual(result["documents"], [["Passage A"]])
        self.assertEqual(result["distances"], [[0.1]])


if __name__ == "__main__":
    unittest.main()
