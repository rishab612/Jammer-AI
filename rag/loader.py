from pathlib import Path

from pypdf import PdfReader
from docx import Document


class DocumentLoader:

    SUPPORTED_EXTENSIONS = {
        ".txt",
        ".md",
        ".pdf",
        ".docx",
    }

    def load(self, file_path):

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {file_path}"
            )

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {extension}"
            )

        if extension in [".txt", ".md"]:
            return self._load_text(path)

        if extension == ".pdf":
            return self._load_pdf(path)

        if extension == ".docx":
            return self._load_docx(path)

    def _load_text(self, path):

        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        return {
            "text": text,
            "source": str(path)
        }

    def _load_pdf(self, path):

        reader = PdfReader(str(path))

        pages = []

        for page in reader.pages:

            text = page.extract_text()

            if text:
                pages.append(text)

        return {
            "text": "\n".join(pages),
            "source": str(path)
        }

    def _load_docx(self, path):

        document = Document(str(path))

        paragraphs = []

        for paragraph in document.paragraphs:

            if paragraph.text.strip():
                paragraphs.append(
                    paragraph.text
                )

        return {
            "text": "\n".join(paragraphs),
            "source": str(path)
        }