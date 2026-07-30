from app.embeddings.providers import FakeEmbeddingProvider


def test_fake_embedding_provider_is_deterministic() -> None:
    provider = FakeEmbeddingProvider(8)
    assert provider.embed(["hello"]) == provider.embed(["hello"])

