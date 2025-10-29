"""
Check consistency across aligned paragraphs.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

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
        """Check for monetary value inconsistencies."""
        differences = []

        # Get monetary values for each language
        monetary = {
            'en': entities['en']['monetary'],
            'de': entities['de']['monetary'],
            'lv': entities['lv']['monetary']
        }

        # Find the maximum number of monetary values in any version
        max_count = max(len(vals) for vals in monetary.values())

        if max_count == 0:
            return differences

        # Check each monetary value position
        for i in range(max_count):
            en_val = monetary['en'][i] if i < len(monetary['en']) else None
            de_val = monetary['de'][i] if i < len(monetary['de']) else None
            lv_val = monetary['lv'][i] if i < len(monetary['lv']) else None

            # Check if any is missing
            if not all([en_val, de_val, lv_val]):
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': en_val.original_text if en_val else "MISSING",
                        'de': de_val.original_text if de_val else "MISSING",
                        'lv': lv_val.original_text if lv_val else "MISSING"
                    },
                    description="Monetary value present in some languages but missing in others",
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

        return differences

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
        """Check for legal reference inconsistencies."""
        differences = []

        legal = {
            'en': entities['en']['legal'],
            'de': entities['de']['legal'],
            'lv': entities['lv']['legal']
        }

        max_count = max(len(refs) for refs in legal.values())
        if max_count == 0:
            return differences

        for i in range(max_count):
            en_ref = legal['en'][i] if i < len(legal['en']) else None
            de_ref = legal['de'][i] if i < len(legal['de']) else None
            lv_ref = legal['lv'][i] if i < len(legal['lv']) else None

            # Check if any is missing
            if not all([en_ref, de_ref, lv_ref]):
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': en_ref.original_text if en_ref else "MISSING",
                        'de': de_ref.original_text if de_ref else "MISSING",
                        'lv': lv_ref.original_text if lv_ref else "MISSING"
                    },
                    description="Legal reference present in some languages but missing in others",
                    confidence=0.95
                ))
                continue

            # Check if references match (normalize and compare)
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

        return differences

    def _normalize_legal_ref(self, ref: str) -> str:
        """Normalize legal reference for comparison."""
        return ref.replace(' ', '').lower()

    def _check_dates(
        self,
        aligned: AlignedParagraphs,
        entities: Dict[str, Dict]
    ) -> List[Difference]:
        """Check for date inconsistencies."""
        differences = []

        dates = {
            'en': entities['en']['dates'],
            'de': entities['de']['dates'],
            'lv': entities['lv']['dates']
        }

        max_count = max(len(d) for d in dates.values())
        if max_count == 0:
            return differences

        for i in range(max_count):
            en_date = dates['en'][i] if i < len(dates['en']) else None
            de_date = dates['de'][i] if i < len(dates['de']) else None
            lv_date = dates['lv'][i] if i < len(dates['lv']) else None

            # Check for vague dates (missing specific values)
            vague_langs = []
            if en_date and en_date.is_vague:
                vague_langs.append('en')
            if de_date and de_date.is_vague:
                vague_langs.append('de')
            if lv_date and lv_date.is_vague:
                vague_langs.append('lv')

            if vague_langs and len(vague_langs) < 3:
                differences.append(Difference(
                    paragraph_ids=aligned.get_paragraph_ids(),
                    error_type="MISSING_VALUE",
                    severity=ERROR_TYPES["MISSING_VALUE"],
                    values={
                        'en': en_date.original_text if en_date else "MISSING",
                        'de': de_date.original_text if de_date else "MISSING",
                        'lv': lv_date.original_text if lv_date else "MISSING"
                    },
                    description=f"Vague date in {', '.join(vague_langs)} while others have specific dates",
                    confidence=0.9
                ))

            # Check if dates match (ignore format, compare actual dates)
            if all([en_date, de_date, lv_date]) and \
               all([en_date.date, de_date.date, lv_date.date]):

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
