"""
Generate embeddings using Watson AI or local sentence transformers.
"""
import os
import json
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict
from config import WATSON_API_KEY, WATSON_URL, WATSON_PROJECT_ID, CACHE_DIR, EMBEDDING_MODEL


class EmbeddingGenerator:
    """Generate embeddings for text using Watson AI or local model."""

    def __init__(self, use_watson: bool = None):
        """
        Initialize the embedding generator.

        Args:
            use_watson: If True, use Watson AI. If False, use local model.
                       If None, auto-detect based on API key availability.
        """
        if use_watson is None:
            use_watson = bool(WATSON_API_KEY and WATSON_PROJECT_ID)

        self.use_watson = use_watson
        self.model = None

        if self.use_watson:
            self._init_watson()
        else:
            self._init_local()

    def _init_watson(self):
        """Initialize Watson AI embeddings."""
        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import Embeddings

            credentials = Credentials(
                url=WATSON_URL,
                api_key=WATSON_API_KEY
            )

            self.model = Embeddings(
                model_id="ibm/slate-125m-english-rtrvr",
                credentials=credentials,
                project_id=WATSON_PROJECT_ID
            )
            print("✓ Using Watson AI embeddings")
        except Exception as e:
            print(f"⚠ Watson AI initialization failed: {e}")
            print("→ Falling back to local model")
            self._init_local()

    def _init_local(self):
        """Initialize local sentence transformer model."""
        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(EMBEDDING_MODEL)
            self.use_watson = False
            print(f"✓ Using local embeddings: {EMBEDDING_MODEL}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize embedding model: {e}")

    def generate(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings

        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        if not texts:
            return np.array([])

        if self.use_watson:
            return self._generate_watson(texts)
        else:
            return self._generate_local(texts)

    def _generate_watson(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using Watson AI."""
        embeddings = self.model.embed_documents(texts)
        return np.array(embeddings)

    def _generate_local(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings using local model."""
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return np.array(embeddings)

    def save_cache(self, embeddings: Dict[str, np.ndarray], cache_name: str):
        """Save embeddings to cache."""
        cache_file = CACHE_DIR / f"{cache_name}_embeddings.npz"
        np.savez(cache_file, **embeddings)
        print(f"✓ Saved embeddings to {cache_file}")

    def load_cache(self, cache_name: str) -> Optional[Dict[str, np.ndarray]]:
        """Load embeddings from cache."""
        cache_file = CACHE_DIR / f"{cache_name}_embeddings.npz"
        if cache_file.exists():
            data = np.load(cache_file)
            print(f"✓ Loaded embeddings from cache: {cache_file}")
            return {key: data[key] for key in data.files}
        return None


if __name__ == "__main__":
    # Test embeddings
    generator = EmbeddingGenerator(use_watson=False)  # Use local for testing

    test_texts = [
        "REGULATION (EU) 2025/… OF THE EUROPEAN PARLIAMENT",
        "of 18 March 2025",
        "establishing the Reform and Growth Facility"
    ]

    embeddings = generator.generate(test_texts)
    print(f"\nGenerated embeddings shape: {embeddings.shape}")
    print(f"First embedding (first 5 dims): {embeddings[0][:5]}")

    # Test caching
    generator.save_cache({"test": embeddings}, "test")
    loaded = generator.load_cache("test")
    print(f"\nLoaded from cache: {loaded['test'].shape}")
