from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Protocol

from app.core.config import Settings


class EmbeddingProvider(Protocol):
    model_id: str

    def verify(self) -> None: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbeddingProvider:
    def __init__(self, dimension: int) -> None:
        self.dimension = dimension
        self.model_id = f"fake-{dimension}"

    def verify(self) -> None:
        return None

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            vector = [((digest[i % len(digest)] / 255.0) * 2) - 1 for i in range(self.dimension)]
            norm = math.sqrt(sum(v * v for v in vector)) or 1.0
            vectors.append([v / norm for v in vector])
        return vectors


class SentenceTransformerProvider(FakeEmbeddingProvider):
    def __init__(self, model_path: Path, dimension: int) -> None:
        super().__init__(dimension)
        self.model_path = model_path
        self.model_id = str(model_path)
        self._model = None

    def verify(self) -> None:
        if not self.model_path.exists():
            raise RuntimeError(f"embedding model path does not exist: {self.model_path}")
        if not any(self.model_path.iterdir()):
            raise RuntimeError(f"embedding model directory is empty: {self.model_path}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(str(self.model_path), local_files_only=True)
        return self._model.encode(texts, normalize_embeddings=True).tolist()


class OnnxEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self, model_path: Path, dimension: int) -> None:
        super().__init__(dimension)
        self.model_path = model_path
        self.model_id = str(model_path)

    def verify(self) -> None:
        if not self.model_path.exists():
            raise RuntimeError(f"onnx model path does not exist: {self.model_path}")


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "sentence_transformers":
        return SentenceTransformerProvider(settings.embedding_model_path, settings.embedding_dimension)
    if settings.embedding_provider == "onnx":
        return OnnxEmbeddingProvider(settings.embedding_model_path, settings.embedding_dimension)
    return FakeEmbeddingProvider(settings.embedding_dimension)

