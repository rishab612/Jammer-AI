import re


class TextChunker:

    def __init__(
        self,
        chunk_size=800,
        overlap=120,
        min_chunk_size=100
    ):

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    # =================================================
    # NORMALIZE TEXT
    # =================================================

    def _normalize_text(self, text):

        # Normalize line endings
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Remove excessive blank lines
        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        # Remove excessive spaces
        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        return text.strip()

    # =================================================
    # SPLIT INTO PARAGRAPHS
    # =================================================

    def _split_paragraphs(self, text):

        paragraphs = re.split(
            r"\n\s*\n",
            text
        )

        paragraphs = [
            paragraph.strip()
            for paragraph in paragraphs
            if paragraph.strip()
        ]

        return paragraphs

    # =================================================
    # SPLIT LONG PARAGRAPH
    # =================================================

    def _split_long_paragraph(
        self,
        paragraph
    ):

        sentences = re.split(
            r"(?<=[.!?])\s+",
            paragraph
        )

        chunks = []

        current = ""

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            # If adding this sentence stays within
            # the chunk size, keep it together.
            if (
                len(current)
                + len(sentence)
                + 1
                <= self.chunk_size
            ):

                if current:

                    current += " "

                current += sentence

            else:

                if current:

                    chunks.append(
                        current.strip()
                    )

                # A single sentence can itself be
                # larger than the chunk size.
                if len(sentence) > self.chunk_size:

                    start = 0

                    while start < len(sentence):

                        end = (
                            start
                            + self.chunk_size
                        )

                        piece = (
                            sentence[start:end]
                            .strip()
                        )

                        if piece:
                            chunks.append(piece)

                        if end >= len(sentence):
                            break

                        start = (
                            end
                            - self.overlap
                        )

                    current = ""

                else:

                    current = sentence

        if current:

            chunks.append(
                current.strip()
            )

        return chunks

    # =================================================
    # MAIN SPLIT
    # =================================================

    def split(self, text):

        text = self._normalize_text(
            text
        )

        if not text:
            return []

        paragraphs = (
            self._split_paragraphs(
                text
            )
        )

        chunks = []

        current_chunk = ""

        for paragraph in paragraphs:

            # -------------------------------------------------
            # Handle paragraphs larger than chunk size
            # -------------------------------------------------

            if len(paragraph) > self.chunk_size:

                if current_chunk:

                    chunks.append(
                        current_chunk.strip()
                    )

                    current_chunk = ""

                long_chunks = (
                    self._split_long_paragraph(
                        paragraph
                    )
                )

                chunks.extend(
                    long_chunks
                )

                continue

            # -------------------------------------------------
            # Add paragraph to current chunk
            # -------------------------------------------------

            if not current_chunk:

                current_chunk = paragraph

            elif (
                len(current_chunk)
                + len(paragraph)
                + 2
                <= self.chunk_size
            ):

                current_chunk += (
                    "\n\n"
                    + paragraph
                )

            else:

                chunks.append(
                    current_chunk.strip()
                )

                # Keep a small amount of overlap
                # from the previous chunk.
                overlap_text = (
                    current_chunk[
                        -self.overlap:
                    ]
                ).strip()

                if (
                    overlap_text
                    and len(overlap_text)
                    >= self.min_chunk_size
                ):

                    current_chunk = (
                        overlap_text
                        + "\n\n"
                        + paragraph
                    )

                else:

                    current_chunk = paragraph

        # -------------------------------------------------
        # Add final chunk
        # -------------------------------------------------

        if current_chunk:

            chunks.append(
                current_chunk.strip()
            )

        # -------------------------------------------------
        # Remove tiny chunks
        # -------------------------------------------------

        chunks = [
            chunk
            for chunk in chunks
            if len(chunk)
            >= self.min_chunk_size
        ]

        return chunks