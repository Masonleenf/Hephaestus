from __future__ import annotations

import math
import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Protocol

from .utils import stable_hash


class VectorAdapter(Protocol):
    name: str
    status: str

    def embed(self, text: str) -> list[float]:
        ...


@dataclass
class LocalHashingVectorAdapter:
    """Deterministic local semantic fallback.

    This is not a mock: it is a stable hashed bag-of-words vector that works
    without provider keys. Hosted embeddings can replace it behind the same
    adapter boundary.
    """

    dimensions: int = 96
    name: str = "local_hashing"
    status: str = "available"

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            digest = stable_hash(token, length=16)
            bucket = int(digest[:8], 16) % self.dimensions
            sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
            vector[bucket] += sign * (1.0 + min(len(token), 16) / 16.0)
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 6) for value in vector]


@dataclass
class OpenAIEmbeddingAdapter:
    """Hosted embedding adapter with an explicit provider boundary."""

    api_key: str
    model: str = "text-embedding-3-small"
    dimensions: int | None = None
    name: str = "openai_embeddings"
    status: str = "available"

    @classmethod
    def from_env(cls) -> "OpenAIEmbeddingAdapter | UnavailableVectorAdapter":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return UnavailableVectorAdapter("openai_embeddings", "OPENAI_API_KEY is not set")
        model = os.environ.get("ONTOLOGY_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        dimensions = os.environ.get("ONTOLOGY_OPENAI_EMBEDDING_DIMENSIONS")
        return cls(api_key=api_key, model=model, dimensions=int(dimensions) if dimensions else None)

    def embed(self, text: str) -> list[float]:
        payload: dict[str, object] = {"model": self.model, "input": text}
        if self.dimensions:
            payload["dimensions"] = self.dimensions
        request = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        return [float(value) for value in body["data"][0]["embedding"]]


@dataclass
class UnavailableVectorAdapter:
    name: str
    reason: str
    status: str = "unavailable"

    def embed(self, text: str) -> list[float]:
        raise RuntimeError(f"vector adapter unavailable: {self.name}: {self.reason}")


def build_vector_adapter(provider: str) -> VectorAdapter:
    if provider == "local_hashing":
        return LocalHashingVectorAdapter()
    if provider == "openai":
        return OpenAIEmbeddingAdapter.from_env()
    if provider == "auto":
        candidate = OpenAIEmbeddingAdapter.from_env()
        return candidate if candidate.status == "available" else LocalHashingVectorAdapter()
    return UnavailableVectorAdapter(provider, "unknown vector provider")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{1,}", text)]


def cosine_similarity(left: Iterable[float], right: Iterable[float]) -> float:
    left_values = list(left)
    right_values = list(right)
    if not left_values or not right_values:
        return 0.0
    dot = sum(a * b for a, b in zip(left_values, right_values))
    left_norm = math.sqrt(sum(a * a for a in left_values))
    right_norm = math.sqrt(sum(b * b for b in right_values))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
