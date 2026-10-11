from core.model import JammerModel
from core.chat import JammerChat

from memory.database import initialize_database
from memory.manager import MemoryManager
from memory.extractor import MemoryExtractor

from rag.pipeline import RAGPipeline

from tools.setup import create_tool_registry
from tools.agent import JammerAgent


VERSION = "2.2.0"


# =========================================================
# BANNER
# =========================================================

def print_banner():

    print()
    print("=" * 60)
    print("                    JAMMER AI")
    print("=" * 60)
    print(f"                    Version {VERSION}")
    print("              Local AI Assistant")
    print("=" * 60)
    print()

    print("Type /help for available commands.")
    print("Type /exit to quit.")
    print()


# =========================================================
# HELP
# =========================================================

def print_help():

    print()
    print("JAMMER COMMANDS")
    print("-" * 40)

    print("/help          Show available commands")
    print("/clear         Clear conversation history")

    print()
    print("MEMORY COMMANDS")
    print("-" * 40)

    print("/memory        Show stored memories")
    print("/remember      Store a new memory")
    print("/forget ID     Delete a memory")
    print("/clear-memory  Delete all memories")

    print()
    print("RAG DOCUMENT COMMANDS")
    print("-" * 40)

    print("/add-doc PATH  Add a document to Jammer")
    print("/documents     Show indexed documents")
    print("/search QUERY  Search your documents")
    print("/clear-docs    Delete all indexed documents")

    print()
    print("SUPPORTED DOCUMENTS")
    print("-" * 40)

    print(".txt")
    print(".md")
    print(".pdf")
    print(".docx")

    print()
    print("TOOL SYSTEM")
    print("-" * 40)

    print("Jammer can use local tools for:")
    print("- Mathematical calculations")
    print("- Date and time")
    print("- Filesystem inspection")
    print("- CPU and RAM information")
    print("- Python execution (permission controlled)")

    print()
    print("SYSTEM COMMANDS")
    print("-" * 40)

    print("/status        Show Jammer status")
    print("/model         Show loaded model")
    print("/about         About Jammer")
    print("/exit          Exit Jammer")

    print()


# =========================================================
# STATUS
# =========================================================

def print_status(registry=None):

    print()
    print("JAMMER STATUS")
    print("-" * 40)

    print("Status       : Online")
    print("Model        : Qwen3-4B Q4_K_M")
    print("Inference    : Local")
    print("GPU          : NVIDIA GTX 1650")
    print("CUDA         : Enabled")
    print("Memory       : SQLite")
    print("RAG          : ChromaDB")
    print("Embeddings   : all-MiniLM-L6-v2")
    print("External API : None")

    if registry is not None:
        print(
            f"Tools        : {registry.count()}"
        )

    print()


# =========================================================
# MODEL INFORMATION
# =========================================================

def print_model():

    print()
    print("MODEL INFORMATION")
    print("-" * 40)

    print("Model        : Qwen3-4B")
    print("Quantization : Q4_K_M")
    print("Format       : GGUF")
    print("Context      : 2048 tokens")
    print("GPU Layers   : All possible")

    print()


# =========================================================
# ABOUT
# =========================================================

def print_about():

    print()
    print("ABOUT JAMMER")
    print("-" * 40)

    print("Jammer is a locally running AI assistant.")
    print("It uses a local Qwen3 language model.")
    print("Inference is performed on this computer.")
    print("Memory is stored locally using SQLite.")
    print("Documents are stored locally using ChromaDB.")
    print("Embeddings are generated locally.")
    print("Tools are executed locally.")
    print("No external AI inference API is required.")

    print()


# =========================================================
# MEMORY
# =========================================================

def show_memories(memory_manager):

    memories = memory_manager.get_all_memories()

    print()

    if not memories:

        print(
            "Jammer: I don't have any stored memories yet."
        )

        print()
        return

    print("JAMMER MEMORY")
    print("-" * 50)

    for memory in memories:

        print(
            f"[{memory['id']}] "
            f"{memory['memory']}"
        )

    print()


def remember(memory_manager):

    print()

    memory = input(
        "Memory to store: "
    ).strip()

    if not memory:

        print(
            "Jammer: Memory cannot be empty."
        )

        return

    memory_manager.add_memory(
        memory
    )

    print(
        "Jammer: Memory saved locally."
    )


def forget(
    memory_manager,
    command
):

    parts = command.split()

    if len(parts) != 2:

        print(
            "Usage: /forget ID"
        )

        return

    try:

        memory_id = int(
            parts[1]
        )

    except ValueError:

        print(
            "Jammer: ID must be a number."
        )

        return

    deleted = memory_manager.delete_memory(
        memory_id
    )

    if deleted:

        print(
            f"Jammer: Memory {memory_id} deleted."
        )

    else:

        print(
            f"Jammer: Memory {memory_id} was not found."
        )


def clear_memory(memory_manager):

    print()

    confirmation = input(
        "Delete ALL stored memories? Type YES to confirm: "
    ).strip()

    if confirmation == "YES":

        memory_manager.clear_memories()

        print(
            "Jammer: All memories have been deleted."
        )

    else:

        print(
            "Jammer: Memory deletion cancelled."
        )


# =========================================================
# AUTOMATIC MEMORY DETECTION
# =========================================================

def check_for_memory(
    user_input,
    memory_manager,
    memory_extractor
):

    detected = memory_extractor.detect(
        user_input
    )

    if not detected:
        return

    memory = detected["memory"]
    category = detected["category"]

    print()

    print(
        "Jammer: I detected information "
        "that may be useful to remember:"
    )

    print(
        f'        "{memory}"'
    )

    print()

    confirmation = input(
        "Jammer: Should I remember this? [Y/N]: "
    ).strip().lower()

    if confirmation in (
        "y",
        "yes"
    ):

        memory_manager.add_memory(
            memory,
            category
        )

        print()

        print(
            "Jammer: I'll remember that."
        )

    else:

        print()

        print(
            "Jammer: Okay, I won't save it."
        )

    print()


# =========================================================
# ADD DOCUMENT
# =========================================================

def add_document(
    rag_pipeline,
    command
):

    parts = command.split(
        maxsplit=1
    )

    if len(parts) != 2:

        print()
        print(
            "Usage: /add-doc <file_path>"
        )

        print()

        return

    file_path = (
        parts[1]
        .strip()
        .strip('"')
    )

    print()

    print(
        "Jammer: Loading document..."
    )

    try:

        chunks = rag_pipeline.add_document(
            file_path
        )

        if chunks == 0:

            print(
                "Jammer: The document "
                "contains no readable text."
            )

        else:

            print(
                "Jammer: Document added successfully."
            )

            print(
                f"Chunks indexed: {chunks}"
            )

    except Exception as error:

        print()

        print(
            "Jammer: Could not add the document."
        )

        print(
            f"Error: {error}"
        )

    print()


# =========================================================
# SHOW DOCUMENTS
# =========================================================

def show_documents(
    rag_pipeline
):

    documents = rag_pipeline.list_documents()

    print()

    print("JAMMER DOCUMENTS")
    print("-" * 50)

    if not documents:

        print(
            "No documents are currently indexed."
        )

        print()

        return

    for index, document in enumerate(
        documents,
        start=1
    ):

        print(
            f"{index}. "
            f"{document['document_name']}"
        )

        print(
            f"   {document['source']}"
        )

    print()

    print(
        f"Total documents: {len(documents)}"
    )

    print(
        f"Total chunks: {rag_pipeline.chunk_count()}"
    )

    print()


# =========================================================
# SEARCH DOCUMENTS
# =========================================================

def search_documents(
    rag_pipeline,
    command
):

    parts = command.split(
        maxsplit=1
    )

    if len(parts) != 2:

        print()

        print(
            "Usage: /search <question>"
        )

        print()

        return

    query = parts[1].strip()

    try:

        results = rag_pipeline.search(
            query,
            n_results=3
        )

        documents = results.get(
            "documents",
            [[]]
        )[0]

        metadatas = results.get(
            "metadatas",
            [[]]
        )[0]

        if not documents:

            print()

            print(
                "Jammer: No relevant documents found."
            )

            print()

            return

        print()

        print("RAG SEARCH RESULTS")
        print("=" * 60)

        for index, document in enumerate(
            documents,
            start=1
        ):

            print()

            print(
                f"Result {index}"
            )

            print(
                "-" * 60
            )

            if index <= len(metadatas):

                metadata = (
                    metadatas[index - 1]
                )

                print(
                    "Source: "
                    f"{metadata.get('document_name', 'Unknown')}"
                )

            print()

            print(document)

        print()

    except Exception as error:

        print()

        print(
            "Jammer: Search failed."
        )

        print(
            f"Error: {error}"
        )

        print()


# =========================================================
# CLEAR DOCUMENTS
# =========================================================

def clear_documents(
    rag_pipeline
):

    print()

    confirmation = input(
        "Delete ALL indexed documents? "
        "Type YES to confirm: "
    ).strip()

    if confirmation == "YES":

        rag_pipeline.clear_documents()

        print()

        print(
            "Jammer: All indexed documents "
            "have been removed."
        )

    else:

        print()

        print(
            "Jammer: Document deletion cancelled."
        )

    print()


# =========================================================
# MAIN
# =========================================================

def main():

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    initialize_database()

    memory_manager = MemoryManager()

    memory_extractor = MemoryExtractor()

    # -----------------------------------------------------
    # BANNER
    # -----------------------------------------------------

    print_banner()

    # -----------------------------------------------------
    # RAG
    # -----------------------------------------------------

    print(
        "Initializing local RAG system..."
    )

    try:

        rag_pipeline = RAGPipeline()

    except Exception as error:

        print()

        print(
            "Failed to initialize RAG system."
        )

        print(
            f"Error: {error}"
        )

        return

    print(
        "RAG system ready."
    )

    print()

    # -----------------------------------------------------
    # MODEL
    # -----------------------------------------------------

    model = JammerModel()

    # -----------------------------------------------------
    # TOOL SYSTEM
    # -----------------------------------------------------

    print(
        "Initializing local tool system..."
    )

    try:

        registry = create_tool_registry()

        agent = JammerAgent(
            registry
        )

    except Exception as error:

        print()

        print(
            "Failed to initialize tool system."
        )

        print(
            f"Error: {error}"
        )

        return

    print(
        f"Tool system ready. "
        f"Available tools: {registry.count()}"
    )

    print()

    # -----------------------------------------------------
    # CHAT
    # -----------------------------------------------------

    chat = JammerChat(
        model,
        memory_manager,
        rag_pipeline,
        agent
    )

    # -----------------------------------------------------
    # MAIN LOOP
    # -----------------------------------------------------

    while True:

        try:

            user_input = input(
                "\nYou: "
            ).strip()

        except KeyboardInterrupt:

            print(
                "\n\nJammer: Goodbye!"
            )

            break

        except EOFError:

            print(
                "\n\nJammer: Goodbye!"
            )

            break

        if not user_input:

            continue

        command = user_input.lower()

        # -------------------------------------------------
        # EXIT
        # -------------------------------------------------

        if command == "/exit":

            print(
                "\nJammer: Goodbye!"
            )

            break

        # -------------------------------------------------
        # HELP
        # -------------------------------------------------

        elif command == "/help":

            print_help()

            continue

        # -------------------------------------------------
        # CLEAR CHAT
        # -------------------------------------------------

        elif command == "/clear":

            chat.clear()

            print(
                "\nJammer: Conversation history cleared."
            )

            continue

        # -------------------------------------------------
        # MEMORY
        # -------------------------------------------------

        elif command == "/memory":

            show_memories(
                memory_manager
            )

            continue

        elif command == "/remember":

            remember(
                memory_manager
            )

            continue

        elif command.startswith("/forget"):

            forget(
                memory_manager,
                user_input
            )

            continue

        elif command == "/clear-memory":

            clear_memory(
                memory_manager
            )

            continue

        # -------------------------------------------------
        # RAG DOCUMENTS
        # -------------------------------------------------

        elif command.startswith("/add-doc"):

            add_document(
                rag_pipeline,
                user_input
            )

            continue

        elif command == "/documents":

            show_documents(
                rag_pipeline
            )

            continue

        elif command.startswith("/search"):

            search_documents(
                rag_pipeline,
                user_input
            )

            continue

        elif command == "/clear-docs":

            clear_documents(
                rag_pipeline
            )

            continue

        # -------------------------------------------------
        # SYSTEM
        # -------------------------------------------------

        elif command == "/status":

            print_status(
                registry
            )

            continue

        elif command == "/model":

            print_model()

            continue

        elif command == "/about":

            print_about()

            continue

        # -------------------------------------------------
        # AUTOMATIC MEMORY DETECTION
        # -------------------------------------------------

        check_for_memory(
            user_input,
            memory_manager,
            memory_extractor
        )

        # -------------------------------------------------
        # AI RESPONSE
        # -------------------------------------------------

        print(
            "\nJammer: ",
            end="",
            flush=True
        )

        try:

            response = chat.send(
                user_input
            )

            print(response)

        except Exception as error:

            print()

            print(
                "Jammer encountered an error:"
            )

            print(error)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    main()