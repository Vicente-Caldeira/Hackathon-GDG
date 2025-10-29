"""
Align paragraphs across multiple language documents using embeddings.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment

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
        # Generate or load embeddings (with index mappings)
        embeddings, index_mappings = self._get_embeddings(documents, use_cache)

        # Align using English as the reference
        return self._align_with_reference(documents, embeddings, index_mappings, 'en')

    def _get_embeddings(
        self,
        documents: Dict[str, Document],
        use_cache: bool
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, List[int]]]:
        """Generate or load embeddings for all documents.

        Returns:
            Tuple of (embeddings, index_mappings) where index_mappings tracks
            which original paragraph indices were embedded.
        """
        # Generate content-based cache key
        cache_name = self.embedding_generator.get_cache_key(documents)

        # Try loading from cache
        if use_cache:
            cached_emb = self.embedding_generator.load_cache(cache_name)
            cached_map = self.embedding_generator.load_mappings(cache_name)

            if cached_emb is not None and cached_map is not None:
                print(f"✓ Loaded embeddings from cache: {cache_name}")
                return cached_emb, cached_map

        # Generate embeddings for each language
        embeddings = {}
        index_mappings = {}

        for lang, doc in documents.items():
            # Track which paragraphs are non-empty
            non_empty_texts = []
            mapping = []

            for i, p in enumerate(doc.paragraphs):
                if p.text.strip():
                    non_empty_texts.append(p.text)
                    mapping.append(i)  # Store original index

            print(f"  Generating embeddings for {lang.upper()}... ({len(non_empty_texts)} non-empty paragraphs)")
            embeddings[lang] = self.embedding_generator.generate(non_empty_texts)
            index_mappings[lang] = mapping

        # Cache for future use
        if use_cache:
            self.embedding_generator.save_cache(embeddings, cache_name)
            self.embedding_generator.save_mappings(index_mappings, cache_name)

        return embeddings, index_mappings

    def _align_with_reference(
        self,
        documents: Dict[str, Document],
        embeddings: Dict[str, np.ndarray],
        index_mappings: Dict[str, List[int]],
        reference_lang: str = 'en'
    ) -> List[AlignedParagraphs]:
        """
        Align all documents using one language as reference.

        Args:
            documents: Dictionary of documents
            embeddings: Dictionary of embeddings
            index_mappings: Mapping from embedding index to original paragraph index
            reference_lang: Language to use as reference (default: 'en')

        Returns:
            List of aligned paragraphs
        """
        ref_doc = documents[reference_lang]
        ref_embeddings = embeddings[reference_lang]
        ref_mapping = index_mappings[reference_lang]

        aligned = []

        # Use global Hungarian assignment for optimal matching
        other_langs = [lang for lang in documents.keys() if lang != reference_lang]

        # Build global matching using Hungarian algorithm for each language pair
        matched_indices = {lang: {} for lang in other_langs}  # Maps emb_idx -> ref_emb_idx

        for lang in other_langs:
            # Compute full cost matrix
            cost_matrix = self._compute_cost_matrix(
                ref_embeddings,
                embeddings[lang]
            )

            # Apply Hungarian algorithm
            ref_indices, lang_indices = linear_sum_assignment(cost_matrix)

            # Store matches that meet threshold
            for ref_i, lang_i in zip(ref_indices, lang_indices):
                similarity = 1.0 - cost_matrix[ref_i, lang_i]  # Convert cost back to similarity
                if similarity >= SIMILARITY_THRESHOLD:
                    matched_indices[lang][lang_i] = (ref_i, similarity)

        # Build aligned paragraphs from global matches
        processed_ref_indices = set()

        for ref_emb_idx in range(len(ref_embeddings)):
            orig_idx = ref_mapping[ref_emb_idx]
            ref_para = ref_doc.paragraphs[orig_idx]

            alignment = {reference_lang: ref_para}
            scores = {}

            # Find matches for this reference paragraph
            for lang in other_langs:
                # Find if any language paragraph matched this ref paragraph
                lang_match = None
                for lang_emb_idx, (matched_ref_idx, sim) in matched_indices[lang].items():
                    if matched_ref_idx == ref_emb_idx:
                        lang_match = (lang_emb_idx, sim)
                        break

                if lang_match:
                    lang_emb_idx, similarity = lang_match
                    orig_para_idx = index_mappings[lang][lang_emb_idx]
                    alignment[lang] = documents[lang].paragraphs[orig_para_idx]
                    scores[f"{reference_lang}-{lang}"] = similarity
                else:
                    alignment[lang] = None
                    scores[f"{reference_lang}-{lang}"] = 0.0

            aligned.append(AlignedParagraphs(
                en=alignment.get('en'),
                de=alignment.get('de'),
                lv=alignment.get('lv'),
                similarity_scores=scores
            ))

            processed_ref_indices.add(ref_emb_idx)

        # CRITICAL: Add unmatched paragraphs from non-reference languages
        # This ensures we detect DE/LV-only content that has no EN equivalent
        for lang in other_langs:
            # Find unmatched embeddings
            matched_lang_indices = set(matched_indices[lang].keys())

            for emb_idx in range(len(embeddings[lang])):
                if emb_idx not in matched_lang_indices:
                    # This paragraph exists in non-reference language but has no match
                    orig_para_idx = index_mappings[lang][emb_idx]

                    # Create alignment with only this language
                    alignment = {
                        'en': None,
                        'de': None,
                        'lv': None
                    }
                    alignment[lang] = documents[lang].paragraphs[orig_para_idx]

                    aligned.append(AlignedParagraphs(
                        en=alignment.get('en'),
                        de=alignment.get('de'),
                        lv=alignment.get('lv'),
                        similarity_scores={}
                    ))

        return aligned

    def _compute_cost_matrix(
        self,
        ref_embeddings: np.ndarray,
        target_embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Compute cost matrix for Hungarian algorithm.

        Args:
            ref_embeddings: Reference embeddings (n, dim)
            target_embeddings: Target embeddings (m, dim)

        Returns:
            Cost matrix (n, m) where cost = 1 - similarity
        """
        # Safety check
        if len(ref_embeddings) == 0 or len(target_embeddings) == 0:
            return np.array([[]])

        # Compute cosine similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(ref_embeddings, target_embeddings)

        # Convert to cost (lower is better for Hungarian)
        cost_matrix = 1.0 - similarities

        return cost_matrix

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
        # Safety check: empty candidate array
        if len(candidate_embeddings) == 0:
            return 0, 0.0

        # Safety check: all candidates excluded
        available_count = len(candidate_embeddings) - len(exclude_indices)
        if available_count <= 0:
            return 0, 0.0

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
