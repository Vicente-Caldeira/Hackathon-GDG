"""
Align paragraphs across multiple language documents using embeddings.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.metrics.pairwise import cosine_similarity

from src.loaders.json_loader import Document, Paragraph
from src.alignment.embeddings import EmbeddingGenerator
from config import SIMILARITY_THRESHOLD


@dataclass
class AlignedParagraphs:
    """Represents aligned paragraphs across languages."""
    en: Optional[Paragraph]
    de: Optional[Paragraph]
    lv: Optional[Paragraph]
    similarity_scores: Dict[str, float]  # Similarity scores for each alignment

    def get_paragraph_ids(self) -> Dict[str, Optional[int]]:
        """Get paragraph numbers for each language."""
        return {
            'en': self.en.para_number if self.en else None,
            'de': self.de.para_number if self.de else None,
            'lv': self.lv.para_number if self.lv else None
        }

    def has_all_languages(self) -> bool:
        """Check if all three languages are present."""
        return self.en is not None and self.de is not None and self.lv is not None

    def __repr__(self):
        ids = self.get_paragraph_ids()
        return f"Aligned(EN:{ids['en']}, DE:{ids['de']}, LV:{ids['lv']})"


class ParagraphAligner:
    """Align paragraphs across multiple documents using embeddings."""

    def __init__(self, embedding_generator: EmbeddingGenerator):
        """
        Initialize the aligner.

        Args:
            embedding_generator: EmbeddingGenerator instance
        """
        self.embedding_generator = embedding_generator

    def align_documents(
        self,
        documents: Dict[str, Document],
        use_cache: bool = True
    ) -> List[AlignedParagraphs]:
        """
        Align paragraphs across all documents.

        Args:
            documents: Dictionary mapping language codes to Document objects
            use_cache: Whether to use cached embeddings

        Returns:
            List of AlignedParagraphs objects
        """
        # Generate or load embeddings
        embeddings = self._get_embeddings(documents, use_cache)

        # Align using English as the reference
        return self._align_with_reference(documents, embeddings, 'en')

    def _get_embeddings(
        self,
        documents: Dict[str, Document],
        use_cache: bool
    ) -> Dict[str, np.ndarray]:
        """Generate or load embeddings for all documents."""
        cache_name = "document_set"

        if use_cache:
            cached = self.embedding_generator.load_cache(cache_name)
            if cached is not None:
                return cached

        # Generate embeddings for each language
        embeddings = {}
        for lang, doc in documents.items():
            texts = [p.text for p in doc.paragraphs if p.text.strip()]
            print(f"Generating embeddings for {lang.upper()}... ({len(texts)} paragraphs)")
            embeddings[lang] = self.embedding_generator.generate(texts)

        # Cache for future use
        if use_cache:
            self.embedding_generator.save_cache(embeddings, cache_name)

        return embeddings

    def _align_with_reference(
        self,
        documents: Dict[str, Document],
        embeddings: Dict[str, np.ndarray],
        reference_lang: str = 'en'
    ) -> List[AlignedParagraphs]:
        """
        Align all documents using one language as reference.

        Args:
            documents: Dictionary of documents
            embeddings: Dictionary of embeddings
            reference_lang: Language to use as reference (default: 'en')

        Returns:
            List of aligned paragraphs
        """
        ref_doc = documents[reference_lang]
        ref_embeddings = embeddings[reference_lang]

        aligned = []

        # Track which paragraphs in other languages have been matched
        matched_indices = {lang: set() for lang in documents.keys() if lang != reference_lang}

        for i, ref_para in enumerate(ref_doc.paragraphs):
            if not ref_para.text.strip():
                continue

            alignment = {reference_lang: ref_para}
            scores = {}

            # Find best match in each other language
            for lang in documents.keys():
                if lang == reference_lang:
                    continue

                best_idx, best_score = self._find_best_match(
                    ref_embeddings[i:i+1],
                    embeddings[lang],
                    matched_indices[lang]
                )

                if best_score >= SIMILARITY_THRESHOLD:
                    alignment[lang] = documents[lang].paragraphs[best_idx]
                    matched_indices[lang].add(best_idx)
                    scores[f"{reference_lang}-{lang}"] = best_score
                else:
                    alignment[lang] = None
                    scores[f"{reference_lang}-{lang}"] = best_score

            aligned.append(AlignedParagraphs(
                en=alignment.get('en'),
                de=alignment.get('de'),
                lv=alignment.get('lv'),
                similarity_scores=scores
            ))

        return aligned

    def _find_best_match(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: np.ndarray,
        exclude_indices: set
    ) -> Tuple[int, float]:
        """
        Find the best matching embedding.

        Args:
            query_embedding: Query embedding (1, dim)
            candidate_embeddings: Candidate embeddings (n, dim)
            exclude_indices: Set of indices to exclude from consideration

        Returns:
            Tuple of (best_index, best_score)
        """
        similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]

        # Mask out excluded indices
        for idx in exclude_indices:
            similarities[idx] = -1

        best_idx = np.argmax(similarities)
        best_score = similarities[best_idx]

        return int(best_idx), float(best_score)


if __name__ == "__main__":
    # Test alignment
    from config import INPUT_FILES
    from src.loaders.json_loader import JSONLoader

    print("Loading documents...")
    documents = JSONLoader.load_all(INPUT_FILES)

    print("\nInitializing embedding generator...")
    generator = EmbeddingGenerator(use_watson=False)

    print("\nAligning paragraphs...")
    aligner = ParagraphAligner(generator)
    aligned = aligner.align_documents(documents, use_cache=False)

    print(f"\n✓ Aligned {len(aligned)} paragraph groups")
    print("\nFirst 5 alignments:")
    for i, group in enumerate(aligned[:5]):
        print(f"{i+1}. {group}")
        if group.has_all_languages():
            print(f"   Scores: {group.similarity_scores}")
        else:
            print(f"   ⚠ Missing languages!")
