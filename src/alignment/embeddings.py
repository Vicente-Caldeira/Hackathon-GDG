"""
Generate embeddings using Watson AI or local sentence transformers.
"""
import os
import json
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Any
from config import (
    WATSON_API_KEY, WATSON_URL, WATSON_PROJECT_ID,
    WATSON_EMBEDDING_MODEL, CACHE_DIR, EMBEDDING_MODEL,
    validate_watson_credentials
)


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
            # Validate credentials first
            if not validate_watson_credentials():
                print("⚠ Watson AI credentials not configured")
                print("→ Falling back to local model")
                self._init_local()
                return

            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import Embeddings

            credentials = Credentials(
                url=WATSON_URL,
                api_key=WATSON_API_KEY
            )

            self.model = Embeddings(
                model_id=WATSON_EMBEDDING_MODEL,  # Use configured model
                credentials=credentials,
                project_id=WATSON_PROJECT_ID
            )
            print(f"✓ Using Watson AI embeddings: {WATSON_EMBEDDING_MODEL}")
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

    def get_model_id(self) -> str:
        """Get the current model identifier."""
        if self.use_watson:
            return WATSON_EMBEDDING_MODEL
        else:
            return EMBEDDING_MODEL

    def _compute_content_hash(self, structured_content: List[Tuple[str, int, str]]) -> str:
        """
        Compute hash of structured content for cache versioning.

        Args:
            structured_content: List of (lang, para_index, text) tuples in order
        """
        hasher = hashlib.md5()
        for lang, idx, text in structured_content:
            # Hash includes language, index, and text to detect reordering/duplication
            entry = f"{lang}:{idx}:{text}"
            hasher.update(entry.encode('utf-8'))
        return hasher.hexdigest()[:8]

    def get_cache_key(self, documents: Dict[str, any]) -> str:
        """Generate versioned cache key from model and structured document content."""
        # Collect structured content: (lang, para_index, text) tuples in stable order
        structured_content = []

        # Process languages in sorted order for consistency
        for lang in sorted(documents.keys()):
            doc = documents[lang]
            for idx, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    structured_content.append((lang, idx, para.text))

        content_hash = self._compute_content_hash(structured_content)
        model_id = self.get_model_id().replace('/', '_').replace('-', '_')
        return f"{model_id}_{content_hash}"

    def save_cache(self, embeddings: Dict[str, np.ndarray], cache_name: str):
        """Save embeddings to cache with metadata."""
        cache_file = CACHE_DIR / f"{cache_name}_embeddings.npz"

        # Add metadata
        metadata = {
            'model_id': self.get_model_id(),
            'use_watson': self.use_watson,
            'embedding_dim': next(iter(embeddings.values())).shape[1] if embeddings else 0
        }

        # Save embeddings and metadata
        cache_data = {**embeddings, '__metadata__': json.dumps(metadata)}
        np.savez(cache_file, **cache_data)

        print(f"✓ Saved embeddings to {cache_file}")
        print(f"  Model: {metadata['model_id']}, Dims: {metadata['embedding_dim']}")

    def load_cache(self, cache_name: str) -> Optional[Dict[str, np.ndarray]]:
        """Load embeddings from cache and validate metadata."""
        cache_file = CACHE_DIR / f"{cache_name}_embeddings.npz"

        if not cache_file.exists():
            return None

        try:
            data = np.load(cache_file, allow_pickle=True)

            # Check if metadata exists and validate
            if '__metadata__' in data.files:
                metadata_str = str(data['__metadata__'])
                metadata = json.loads(metadata_str)

                # Validate model matches
                current_model = self.get_model_id()
                cached_model = metadata.get('model_id', 'unknown')

                if cached_model != current_model:
                    print(f"⚠ Cache model mismatch:")
                    print(f"  Cached: {cached_model}")
                    print(f"  Current: {current_model}")
                    print(f"→ Regenerating embeddings with new model")
                    return None

            # Load embeddings (excluding metadata)
            embeddings = {key: data[key] for key in data.files if key != '__metadata__'}

            return embeddings

        except Exception as e:
            print(f"⚠ Cache load failed: {e}")
            print(f"→ Will regenerate embeddings")
            return None

    def save_mappings(self, mappings: Dict[str, List[int]], cache_name: str):
        """Save index mappings to separate JSON file."""
        mapping_file = CACHE_DIR / f"{cache_name}_mappings.json"
        with open(mapping_file, 'w') as f:
            json.dump(mappings, f)

    def load_mappings(self, cache_name: str) -> Optional[Dict[str, List[int]]]:
        """Load index mappings from separate JSON file."""
        mapping_file = CACHE_DIR / f"{cache_name}_mappings.json"

        if not mapping_file.exists():
            return None

        try:
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Mappings load failed: {e}")
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
