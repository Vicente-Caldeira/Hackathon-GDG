"""
Check consistency across aligned paragraphs.
"""
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
from scipy.optimize import linear_sum_assignment

from src.alignment.paragraph_aligner import AlignedParagraphs
from src.extractors.entity_extractor import EntityExtractor, MonetaryValue, LegalReference, DateValue
from config import ERROR_TYPES, NUMERICAL_TOLERANCE


@dataclass
class Difference:
    """Represents a detected difference/inconsistency."""
    paragraph_ids: Dict[str, Optional[int]]
    error_type: str
    severity: str
    values: Dict[str, str]
    description: str
    confidence: float = 1.0

    def __repr__(self):
        para_str = f"Para({self.paragraph_ids})"
        return f"{para_str} [{self.severity}] {self.error_type}: {self.description}"


class ConsistencyChecker:
    """Check for inconsistencies across aligned paragraphs."""

    def __init__(self):
        self.extractor = EntityExtractor()

    def check_all(self, aligned_paragraphs: List[AlignedParagraphs]) -> List[Difference]:
        """
        Check all aligned paragraphs for inconsistencies.

        Args:
            aligned_paragraphs: List of AlignedParagraphs

        Returns:
            List of detected differences
        """
        all_differences = []

        for aligned in aligned_paragraphs:
            if not aligned.has_all_languages():
                # Flag missing paragraphs
                diff = self._check_missing_paragraphs(aligned)
                if diff:
                    all_differences.append(diff)

                # CRITICAL: Compare available languages even when one is missing
                # This catches DE-LV inconsistencies when EN is absent
                available_langs = []
                entities = {}

                if aligned.en:
                    available_langs.append('en')
                    entities['en'] = self.extractor.extract_all(aligned.en.text)
                if aligned.de:
                    available_langs.append('de')
                    entities['de'] = self.extractor.extract_all(aligned.de.text)
                if aligned.lv:
                    available_langs.append('lv')
                    entities['lv'] = self.extractor.extract_all(aligned.lv.text)

                # Compare available pairs
                if len(available_langs) >= 2:
                    partial_diffs = self._check_partial_alignment(aligned, entities, available_langs)
                    all_differences.extend(partial_diffs)

                continue

            # Extract entities from all three versions
            entities = {
                'en': self.extractor.extract_all(aligned.en.text),
                'de': self.extractor.extract_all(aligned.de.text),
                'lv': self.extractor.extract_all(aligned.lv.text)
            }

            # Check each type of entity
            differences = []
            differences.extend(self._check_monetary_values(aligned, entities))
            differences.extend(self._check_legal_references(aligned, entities))
            differences.extend(self._check_dates(aligned, entities))

            all_differences.extend(differences)

        return all_differences

    def _check_missing_paragraphs(self, aligned: AlignedParagraphs) -> Optional[Difference]:
        """Check for missing paragraphs in any language."""
        para_ids = aligned.get_paragraph_ids()
        missing = [lang for lang, para_id in para_ids.items() if para_id is None]

        if missing:
            return Difference(
                paragraph_ids=para_ids,
                error_type="MISSING_PARAGRAPH",
                severity=ERROR_TYPES.get("MISSING_VALUE", "CRITICAL"),
                values={lang: "MISSING" if lang in missing else "PRESENT" for lang in ['en', 'de', 'lv']},
                description=f"Paragraph missing in {', '.join(missing)}",
                confidence=1.0
            )
        return None

    def _check_monetary_values(
        self,
        aligned: AlignedParagraphs,
        entities: Dict[str, Dict]
    ) -> List[Difference]:
        """Check for monetary value inconsistencies using value-driven matching."""
        differences = []

        # Get monetary values for each language
        monetary = {
            'en': entities['en']['monetary'],
            'de': entities['de']['monetary'],
            'lv': entities['lv']['monetary']
        }

        if not any(monetary.values()):
            return differences

        # Create optimal matching between EN/DE and EN/LV
        matched_triplets, unmatched = self._match_monetary_values(monetary)

        # Check matched triplets for differences
        for en_val, de_val, lv_val in matched_triplets:
            # If LV is missing, report it specifically
            if lv_val is None:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': en_val.original_text,
                        'de': de_val.original_text,
                        'lv': "MISSING"
                    },
                    description="Monetary value present in EN/DE but missing in LV",
                    confidence=0.95
                ))
                continue

            # Check for currency mismatches
            currencies = {en_val.currency, de_val.currency, lv_val.currency}
            if len(currencies) > 1:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="CURRENCY_MISMATCH",
                    severity=ERROR_TYPES["CURRENCY_MISMATCH"],
                    values={
                        'en': f"{en_val.amount} {en_val.currency}",
                        'de': f"{de_val.amount} {de_val.currency}",
                        'lv': f"{lv_val.amount} {lv_val.currency}"
                    },
                    description=f"Currency mismatch: {currencies}",
                    confidence=1.0
                ))

            # Check for scale mismatches
            scales = {en_val.scale, de_val.scale, lv_val.scale}
            if len(scales) > 1:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="SCALE_ERROR",
                    severity=ERROR_TYPES["SCALE_ERROR"],
                    values={
                        'en': f"{en_val.amount} {en_val.scale}",
                        'de': f"{de_val.amount} {de_val.scale}",
                        'lv': f"{lv_val.amount} {lv_val.scale}"
                    },
                    description=f"Scale mismatch: {scales}",
                    confidence=1.0
                ))

            # Check for amount differences (accounting for scale)
            en_full = en_val.amount * self._scale_multiplier(en_val.scale)
            de_full = de_val.amount * self._scale_multiplier(de_val.scale)
            lv_full = lv_val.amount * self._scale_multiplier(lv_val.scale)

            if not (abs(en_full - de_full) < NUMERICAL_TOLERANCE and
                    abs(en_full - lv_full) < NUMERICAL_TOLERANCE):
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MONETARY_VALUE",
                    severity=ERROR_TYPES["MONETARY_VALUE"],
                    values={
                        'en': en_val.original_text,
                        'de': de_val.original_text,
                        'lv': lv_val.original_text
                    },
                    description=f"Monetary amounts differ: EN={en_full}, DE={de_full}, LV={lv_full}",
                    confidence=0.99
                ))

        # Report unmatched values
        for lang, vals in unmatched.items():
            for val in vals:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': val.original_text if lang == 'en' else "MISSING",
                        'de': val.original_text if lang == 'de' else "MISSING",
                        'lv': val.original_text if lang == 'lv' else "MISSING"
                    },
                    description=f"Monetary value in {lang.upper()} has no matching equivalent in other languages",
                    confidence=0.95
                ))

        return differences

    def _match_monetary_values(
        self, monetary: Dict[str, List[MonetaryValue]]
    ) -> Tuple[List[Tuple[MonetaryValue, MonetaryValue, MonetaryValue]], Dict[str, List[MonetaryValue]]]:
        """
        Match monetary values across languages using Hungarian algorithm.

        Returns:
            (matched_triplets, unmatched_by_lang)
        """
        en_vals = monetary['en']
        de_vals = monetary['de']
        lv_vals = monetary['lv']

        # Track matched indices
        matched_en = set()
        matched_de = set()
        matched_lv = set()
        triplets = []

        # Match EN to DE first
        if en_vals and de_vals:
            cost_matrix = np.zeros((len(en_vals), len(de_vals)))
            for i, en_val in enumerate(en_vals):
                for j, de_val in enumerate(de_vals):
                    cost_matrix[i, j] = self._monetary_distance(en_val, de_val)

            en_indices, de_indices = linear_sum_assignment(cost_matrix)
            # Accept matches even with currency/scale issues (threshold 0.9) so we can report specific errors
            en_de_matches = {en_i: de_i for en_i, de_i in zip(en_indices, de_indices)
                           if cost_matrix[en_i, de_i] < 0.9}
        else:
            en_de_matches = {}

        # For each EN-DE pair, try to find matching LV
        for en_i, de_i in en_de_matches.items():
            # Mark EN-DE as matched regardless of LV
            matched_en.add(en_i)
            matched_de.add(de_i)

            if lv_vals:
                # Find best matching LV value
                best_lv_i = None
                best_dist = float('inf')
                for lv_i, lv_val in enumerate(lv_vals):
                    if lv_i in matched_lv:
                        continue
                    dist = self._monetary_distance(en_vals[en_i], lv_val)
                    if dist < best_dist and dist < 0.9:  # Accept currency/scale issues
                        best_dist = dist
                        best_lv_i = lv_i

                if best_lv_i is not None:
                    triplets.append((en_vals[en_i], de_vals[de_i], lv_vals[best_lv_i]))
                    matched_lv.add(best_lv_i)
                else:
                    # EN-DE pair exists but no LV match - add with None for LV
                    triplets.append((en_vals[en_i], de_vals[de_i], None))
            else:
                # No LV values at all - add EN-DE pair with None for LV
                triplets.append((en_vals[en_i], de_vals[de_i], None))

        # Collect unmatched
        unmatched = {
            'en': [v for i, v in enumerate(en_vals) if i not in matched_en],
            'de': [v for i, v in enumerate(de_vals) if i not in matched_de],
            'lv': [v for i, v in enumerate(lv_vals) if i not in matched_lv]
        }

        return triplets, unmatched

    def _monetary_distance(self, val1: MonetaryValue, val2: MonetaryValue) -> float:
        """Calculate similarity distance between two monetary values (0=identical, 1=completely different)."""
        # Different currency = high cost
        if val1.currency != val2.currency:
            return 0.8

        # Calculate normalized amount difference
        full1 = val1.amount * self._scale_multiplier(val1.scale)
        full2 = val2.amount * self._scale_multiplier(val2.scale)

        if full1 == 0 and full2 == 0:
            return 0.0

        max_val = max(abs(full1), abs(full2))
        if max_val == 0:
            return 0.0

        diff_ratio = abs(full1 - full2) / max_val
        return min(diff_ratio, 1.0)  # Cap at 1.0

    def _scale_multiplier(self, scale: str) -> float:
        """Get multiplier for scale."""
        scale_map = {
            'million': 1e6,
            'billion': 1e9,
            'trillion': 1e12,
            '': 1
        }
        return scale_map.get(scale, 1)

    def _check_legal_references(
        self,
        aligned: AlignedParagraphs,
        entities: Dict[str, Dict]
    ) -> List[Difference]:
        """Check for legal reference inconsistencies using value-driven matching."""
        differences = []

        legal = {
            'en': entities['en']['legal'],
            'de': entities['de']['legal'],
            'lv': entities['lv']['legal']
        }

        if not any(legal.values()):
            return differences

        # Match legal references by value
        matched_triplets, unmatched = self._match_legal_references(legal)

        # Check matched triplets
        for en_ref, de_ref, lv_ref in matched_triplets:
            # Normalize and compare references
            refs_normalized = {
                self._normalize_legal_ref(en_ref.reference),
                self._normalize_legal_ref(de_ref.reference),
                self._normalize_legal_ref(lv_ref.reference)
            }

            if len(refs_normalized) > 1:
                error_type = "ARTICLE_REFERENCE" if en_ref.type == "article" else "LEGAL_REFERENCE"
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type=error_type,
                    severity=ERROR_TYPES.get(error_type, "CRITICAL"),
                    values={
                        'en': en_ref.original_text,
                        'de': de_ref.original_text,
                        'lv': lv_ref.original_text
                    },
                    description=f"Legal reference mismatch: {refs_normalized}",
                    confidence=0.98
                ))

        # Report unmatched references
        for lang, vals in unmatched.items():
            for val in vals:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': val.original_text if lang == 'en' else "MISSING",
                        'de': val.original_text if lang == 'de' else "MISSING",
                        'lv': val.original_text if lang == 'lv' else "MISSING"
                    },
                    description=f"Legal reference in {lang.upper()} has no matching equivalent in other languages",
                    confidence=0.95
                ))

        return differences

    def _match_legal_references(
        self, legal: Dict[str, List[LegalReference]]
    ) -> Tuple[List[Tuple[LegalReference, LegalReference, LegalReference]], Dict[str, List[LegalReference]]]:
        """Match legal references across languages by normalized value."""
        en_vals = legal['en']
        de_vals = legal['de']
        lv_vals = legal['lv']

        matched_en = set()
        matched_de = set()
        matched_lv = set()
        triplets = []

        # Match EN to DE
        if en_vals and de_vals:
            cost_matrix = np.zeros((len(en_vals), len(de_vals)))
            for i, en_val in enumerate(en_vals):
                for j, de_val in enumerate(de_vals):
                    cost_matrix[i, j] = self._legal_ref_distance(en_val, de_val)

            en_indices, de_indices = linear_sum_assignment(cost_matrix)
            en_de_matches = {en_i: de_i for en_i, de_i in zip(en_indices, de_indices)
                           if cost_matrix[en_i, de_i] < 0.5}
        else:
            en_de_matches = {}

        # Match LV to each EN-DE pair
        for en_i, de_i in en_de_matches.items():
            if lv_vals:
                best_lv_i = None
                best_dist = float('inf')
                for lv_i, lv_val in enumerate(lv_vals):
                    if lv_i in matched_lv:
                        continue
                    dist = self._legal_ref_distance(en_vals[en_i], lv_val)
                    if dist < best_dist and dist < 0.5:
                        best_dist = dist
                        best_lv_i = lv_i

                if best_lv_i is not None:
                    triplets.append((en_vals[en_i], de_vals[de_i], lv_vals[best_lv_i]))
                    matched_en.add(en_i)
                    matched_de.add(de_i)
                    matched_lv.add(best_lv_i)

        unmatched = {
            'en': [v for i, v in enumerate(en_vals) if i not in matched_en],
            'de': [v for i, v in enumerate(de_vals) if i not in matched_de],
            'lv': [v for i, v in enumerate(lv_vals) if i not in matched_lv]
        }

        return triplets, unmatched

    def _legal_ref_distance(self, ref1: LegalReference, ref2: LegalReference) -> float:
        """Calculate distance between two legal references (0=same, 1=different)."""
        # Different types = high cost
        if ref1.type != ref2.type:
            return 0.9

        # Compare normalized references
        norm1 = self._normalize_legal_ref(ref1.reference)
        norm2 = self._normalize_legal_ref(ref2.reference)

        if norm1 == norm2:
            return 0.0

        # Calculate string edit distance (Levenshtein-like)
        # Simple approximation: character overlap
        max_len = max(len(norm1), len(norm2))
        if max_len == 0:
            return 0.0

        # Count common characters
        common = sum(1 for a, b in zip(norm1, norm2) if a == b)
        return 1.0 - (common / max_len)

    def _normalize_legal_ref(self, ref: str) -> str:
        """Normalize legal reference for comparison."""
        return ref.replace(' ', '').lower()

    def _check_dates(
        self,
        aligned: AlignedParagraphs,
        entities: Dict[str, Dict]
    ) -> List[Difference]:
        """Check for date inconsistencies using value-driven matching."""
        differences = []

        dates = {
            'en': entities['en']['dates'],
            'de': entities['de']['dates'],
            'lv': entities['lv']['dates']
        }

        if not any(dates.values()):
            return differences

        # Match dates by value
        matched_triplets, unmatched = self._match_dates(dates)

        # Check matched triplets
        for en_date, de_date, lv_date in matched_triplets:
            # Check for vague dates
            vague_langs = []
            if en_date.is_vague:
                vague_langs.append('en')
            if de_date.is_vague:
                vague_langs.append('de')
            if lv_date.is_vague:
                vague_langs.append('lv')

            if vague_langs and len(vague_langs) < 3:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': en_date.original_text,
                        'de': de_date.original_text,
                        'lv': lv_date.original_text
                    },
                    description=f"Vague date in {', '.join(vague_langs)} while others have specific dates",
                    confidence=0.9
                ))

            # Check if dates actually match
            if all([en_date.date, de_date.date, lv_date.date]):
                date_values = {
                    en_date.date.date(),
                    de_date.date.date(),
                    lv_date.date.date()
                }

                if len(date_values) > 1:
                    differences.append(Difference(
                        paragraph_ids=aligned.get_paragraph_ids(),
                        error_type="DATE_VALUE",
                        severity=ERROR_TYPES["DATE_VALUE"],
                        values={
                            'en': en_date.original_text,
                            'de': de_date.original_text,
                            'lv': lv_date.original_text
                        },
                        description=f"Date values differ: {date_values}",
                        confidence=0.99
                    ))

        # Report unmatched dates
        for lang, vals in unmatched.items():
            for val in vals:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': val.original_text if lang == 'en' else "MISSING",
                        'de': val.original_text if lang == 'de' else "MISSING",
                        'lv': val.original_text if lang == 'lv' else "MISSING"
                    },
                    description=f"Date in {lang.upper()} has no matching equivalent in other languages",
                    confidence=0.95
                ))

        return differences

    def _match_dates(
        self, dates: Dict[str, List[DateValue]]
    ) -> Tuple[List[Tuple[DateValue, DateValue, DateValue]], Dict[str, List[DateValue]]]:
        """Match dates across languages by value similarity."""
        en_vals = dates['en']
        de_vals = dates['de']
        lv_vals = dates['lv']

        matched_en = set()
        matched_de = set()
        matched_lv = set()
        triplets = []

        # Match EN to DE
        if en_vals and de_vals:
            cost_matrix = np.zeros((len(en_vals), len(de_vals)))
            for i, en_val in enumerate(en_vals):
                for j, de_val in enumerate(de_vals):
                    cost_matrix[i, j] = self._date_distance(en_val, de_val)

            en_indices, de_indices = linear_sum_assignment(cost_matrix)
            en_de_matches = {en_i: de_i for en_i, de_i in zip(en_indices, de_indices)
                           if cost_matrix[en_i, de_i] < 0.5}
        else:
            en_de_matches = {}

        # Match LV to each EN-DE pair
        for en_i, de_i in en_de_matches.items():
            if lv_vals:
                best_lv_i = None
                best_dist = float('inf')
                for lv_i, lv_val in enumerate(lv_vals):
                    if lv_i in matched_lv:
                        continue
                    dist = self._date_distance(en_vals[en_i], lv_val)
                    if dist < best_dist and dist < 0.5:
                        best_dist = dist
                        best_lv_i = lv_i

                if best_lv_i is not None:
                    triplets.append((en_vals[en_i], de_vals[de_i], lv_vals[best_lv_i]))
                    matched_en.add(en_i)
                    matched_de.add(de_i)
                    matched_lv.add(best_lv_i)

        unmatched = {
            'en': [v for i, v in enumerate(en_vals) if i not in matched_en],
            'de': [v for i, v in enumerate(de_vals) if i not in matched_de],
            'lv': [v for i, v in enumerate(lv_vals) if i not in matched_lv]
        }

        return triplets, unmatched

    def _date_distance(self, date1: DateValue, date2: DateValue) -> float:
        """Calculate distance between two dates (0=same, 1=very different)."""
        # If both parsed, compare actual dates
        if date1.date and date2.date:
            delta = abs((date1.date - date2.date).days)
            # 0 days = 0.0, 365+ days = 1.0
            return min(delta / 365.0, 1.0)

        # If one is vague and one isn't, medium distance
        if date1.is_vague != date2.is_vague:
            return 0.6

        # Both vague, low distance
        return 0.3

    def _check_partial_alignment(
        self,
        aligned: AlignedParagraphs,
        entities: Dict[str, Dict],
        available_langs: List[str]
    ) -> List[Difference]:
        """
        Check consistency for partial alignments (when one or more languages are missing).

        Args:
            aligned: AlignedParagraphs with at least 2 languages
            entities: Extracted entities for available languages
            available_langs: List of available language codes

        Returns:
            List of detected differences
        """
        differences = []

        # Build partial entities dict (fill missing with empty)
        full_entities = {
            'monetary': {lang: entities.get(lang, {}).get('monetary', []) for lang in ['en', 'de', 'lv']},
            'legal': {lang: entities.get(lang, {}).get('legal', []) for lang in ['en', 'de', 'lv']},
            'dates': {lang: entities.get(lang, {}).get('dates', []) for lang in ['en', 'de', 'lv']}
        }

        # Only check if we have data in available languages
        if any(full_entities['monetary'].get(lang) for lang in available_langs):
            diffs = self._check_monetary_values(aligned, {
                lang: {'monetary': full_entities['monetary'][lang],
                       'legal': [], 'dates': []}
                for lang in ['en', 'de', 'lv']
            })
            differences.extend(diffs)

        if any(full_entities['legal'].get(lang) for lang in available_langs):
            diffs = self._check_legal_references(aligned, {
                lang: {'monetary': [], 'legal': full_entities['legal'][lang],
                       'dates': []}
                for lang in ['en', 'de', 'lv']
            })
            differences.extend(diffs)

        if any(full_entities['dates'].get(lang) for lang in available_langs):
            diffs = self._check_dates(aligned, {
                lang: {'monetary': [], 'legal': [],
                       'dates': full_entities['dates'][lang]}
                for lang in ['en', 'de', 'lv']
            })
            differences.extend(diffs)

        return differences


if __name__ == "__main__":
    # Test consistency checker
    from config import INPUT_FILES
    from src.loaders.json_loader import JSONLoader
    from src.alignment.embeddings import EmbeddingGenerator
    from src.alignment.paragraph_aligner import ParagraphAligner

    print("Loading and aligning documents...")
    documents = JSONLoader.load_all(INPUT_FILES)
    generator = EmbeddingGenerator(use_watson=False)
    aligner = ParagraphAligner(generator)
    aligned = aligner.align_documents(documents, use_cache=True)

    print(f"\nChecking consistency across {len(aligned)} aligned paragraphs...")
    checker = ConsistencyChecker()
    differences = checker.check_all(aligned)

    print(f"\n✓ Found {len(differences)} differences")
    print("\nFirst 10 differences:")
    for i, diff in enumerate(differences[:10], 1):
        print(f"{i}. {diff}")
