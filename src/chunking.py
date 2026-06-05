from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        # Tách câu: cắt ngay sau dấu . ! ? rồi tới khoảng trắng.
        raw_sentences = re.split(r"(?<=[.!?])\s+", text)
        # Làm sạch: bỏ khoảng trắng thừa, loại câu rỗng.
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        # Gom mỗi 'max_sentences_per_chunk' câu thành 1 chunk.
        chunks: list[str] = []
        step = self.max_sentences_per_chunk
        for start in range(0, len(sentences), step):
            group = sentences[start : start + step]
            chunks.append(" ".join(group))
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        # Cửa ngõ: giao toàn bộ việc cho helper đệ quy với danh sách separator đầy đủ.
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        # Dừng 1: đoạn đã đủ ngắn → giữ nguyên.
        if len(current_text) <= self.chunk_size:
            return [current_text] if current_text else []

        # Dừng 2: hết separator để thử → cắt cứng theo chunk_size.
        if not remaining_separators:
            return [
                current_text[i : i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        sep = remaining_separators[0]      # separator đang thử
        rest = remaining_separators[1:]    # các separator ưu tiên thấp hơn

        # sep == "" nghĩa là không còn ranh giới → cắt cứng theo chunk_size.
        if sep == "":
            return [
                current_text[i : i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        result: list[str] = []
        for piece in current_text.split(sep):
            if not piece:
                continue
            if len(piece) <= self.chunk_size:
                result.append(piece)
            else:
                # Mảnh vẫn dài → đệ quy với separator ưu tiên thấp hơn.
                result.extend(self._split(piece, rest))
        return result


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    dot = _dot(vec_a, vec_b)                  # tử số: tích vô hướng a·b
    norm_a = math.sqrt(_dot(vec_a, vec_a))    # độ dài vec_a
    norm_b = math.sqrt(_dot(vec_b, vec_b))    # độ dài vec_b
    if norm_a == 0 or norm_b == 0:            # tránh chia cho 0
        return 0.0
    return dot / (norm_a * norm_b)            # công thức cosine


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        # Chạy cả 3 chiến lược trên cùng một text.
        strategies = {
            "fixed_size": FixedSizeChunker(chunk_size=chunk_size).chunk(text),
            "by_sentences": SentenceChunker().chunk(text),
            "recursive": RecursiveChunker(chunk_size=chunk_size).chunk(text),
        }

        result: dict = {}
        for name, chunks in strategies.items():
            count = len(chunks)
            avg_length = (sum(len(c) for c in chunks) / count) if count else 0
            result[name] = {
                "count": count,
                "avg_length": avg_length,
                "chunks": chunks,
            }
        return result
