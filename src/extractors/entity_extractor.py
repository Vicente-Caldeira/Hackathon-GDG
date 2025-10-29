"""
Extract entities from text: dates, monetary values, legal references, etc.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from dateutil import parser as date_parser
from datetime import datetime
import numpy as np

try:
    from src.alignment.embeddings import EmbeddingGenerator
except Exception:  # pragma: no cover - optional dependency
    EmbeddingGenerator = None  # type: ignore


@dataclass
class MonetaryValue:
    """Represents a monetary amount with currency."""
    amount: float
    currency: str
    original_text: str
    scale: str  # 'million', 'billion', etc.

    def __repr__(self):
        return f"{self.amount} {self.scale} {self.currency}"


@dataclass
class LegalReference:
    """Represents a legal reference (regulation, article, etc.)."""
    type: str  # 'regulation', 'article', 'paragraph'
    reference: str
    original_text: str
    normalized: str = ""

    def __repr__(self):
        return f"{self.type}: {self.reference}"


@dataclass
class DateValue:
    """Represents a date."""
    date: Optional[datetime]
    original_text: str
    is_vague: bool  # True if "in 2 weeks", "soon", etc.

    def __repr__(self):
        if self.is_vague:
            return f"VAGUE: {self.original_text}"
        return self.date.strftime("%Y-%m-%d") if self.date else self.original_text


class EntityExtractor:
    """Extract various entities from text."""

    # Regex patterns for monetary values
    CURRENCY_TERMS = r'EURO(?:S)?|EIRO|EUR|USD|GBP|€|\$'
    AMOUNT_PATTERN = r'[0-9]+(?:[.,\s][0-9]{3})*(?:[.,][0-9]+)?'
    SCALE_TERMS = r'million|billion|trillion|Mio\.|Mrd\.|miljonu|miljardi'
    MONETARY_PATTERNS = [
        # EUR 1500 million, EUR 1,500 million, etc.
        rf'({CURRENCY_TERMS})\s*({AMOUNT_PATTERN})\s*({SCALE_TERMS})?',
        # 1500 million EUR, 1,5 Mrd. EUR, etc.
        rf'({AMOUNT_PATTERN})\s*({SCALE_TERMS})?\s*({CURRENCY_TERMS})',
    ]

    # Legal reference patterns (multilingual, refined)
    LEGAL_PATTERNS = {
        'regulation': [
            re.compile(
                r'\b(?:regulation|verordnung|regula(?:s)?)\s*\((?:eu|euratom|eu,\s*euratom)\)\s*(?:no\.?|nr\.?)?\s*(?P<ref>\d{1,4}/\d{1,4})',
                re.IGNORECASE
            ),
            re.compile(
                r'\((?:eu|euratom|eu,\s*euratom)\)\s*(?:no\.?|nr\.?|regulas\s*nr\.?)\s*(?P<ref>\d{1,4}/\d{1,4})',
                re.IGNORECASE
            ),
        ],
        # English: Article, German: Artikel, Latvian: pants/pantu/panta (nom/acc/gen)
        'article': [
            re.compile(
                r'\b(?:art(?:\.|icle)?|artikel|pants|pantu|panta)\s*(?P<ref>\d+[a-z]?(?:\([0-9a-z]+\))*)(?!\s*\.)',
                re.IGNORECASE
            ),
            # Also match pattern: "number. pantu/panta/pants" (Latvian format)
            re.compile(
                r'\b(?P<ref>\d+[a-z]?)\.\s*(?:pants|pantu|panta)\b',
                re.IGNORECASE
            ),
        ],
        # English: Paragraph, German: Absatz, Latvian: rindkopa/punkts
        'paragraph': [
            re.compile(
                r'\b(?:paragraph|absatz|punkt|punkts|punkta|rindkopa)\s*(?P<ref>\d+[a-z]?(?:\([0-9a-z]+\))*)',
                re.IGNORECASE
            ),
            re.compile(
                r'\b(?P<ref>\d+[a-z]?)\.\s*(?:punkt|punkts|punkta)\b',
                re.IGNORECASE
            ),
        ],
        'case': [
            re.compile(
                r'\b(?P<ref>[CT][\-‐‑‒–—―−]?\d+/\d+\s*P?)\b',
                re.IGNORECASE
            ),
        ],
        'ecli': [
            re.compile(
                r'\b(?P<ref>E[CU]LI?:[A-Z]+:\d{4}:\d+)\b',
                re.IGNORECASE
            ),
        ],
    }

    LEGAL_TYPE_NORMALIZATION = {
        'regulation': 'regulation',
        'article': 'article',
        'paragraph': 'paragraph',
        'case': 'case',
        'ecli': 'ecli',
    }

    LEGAL_SIMILARITY_THRESHOLD = 0.88
    _embedding_generator: Optional["EmbeddingGenerator"] = None
    _embedding_generator_failed = False

    # Month name mappings for German and Latvian to English
    MONTH_NAMES = {
        # German
        'januar': 'january', 'februar': 'february', 'märz': 'march',
        'april': 'april', 'mai': 'may', 'juni': 'june',
        'juli': 'july', 'august': 'august', 'september': 'september',
        'oktober': 'october', 'november': 'november', 'dezember': 'december',

        # Latvian nominative
        'janvāris': 'january', 'februāris': 'february', 'marts': 'march',
        'aprīlis': 'april', 'maijs': 'may', 'jūnijs': 'june',
        'jūlijs': 'july', 'augusts': 'august', 'septembris': 'september',
        'oktobris': 'october', 'novembris': 'november', 'decembris': 'december',

        # Latvian genitive (used after "gada")
        'janvāra': 'january', 'februāra': 'february', 'marta': 'march',
        'aprīļa': 'april', 'maija': 'may', 'jūnija': 'june',
        'jūlija': 'july', 'augusta': 'august', 'septembra': 'september',
        'oktobra': 'october', 'novembra': 'november', 'decembra': 'december',

        # Latvian dative (used with "līdz" - until)
        'janvāram': 'january', 'februāram': 'february', 'martam': 'march',
        'aprīlim': 'april', 'maijam': 'may', 'jūnijam': 'june',
        'jūlijam': 'july', 'augustam': 'august', 'septembrim': 'september',
        'oktobrim': 'october', 'novembrim': 'november', 'decembrim': 'december',
    }

    # Date patterns (multilingual)
    DATE_PATTERNS = [
        r'\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}',  # 16/06/2023, 2023-06-16
        r'\d{4}[-‑]\d{2}[-‑]\d{2}',             # 2023-06-16

        # English months - with optional prepositions
        r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',

        # German months - with optional prepositions (vom/im)
        r'(?:vom|im)?\s*\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}',
        # German month-only with year (im Juni 1993)
        r'(?:im|vom)\s+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}',

        # Latvian full format: "YYYY. gada DD. [month]" (genitive or nominative)
        r'\d{4}\.\s*gada\s+\d{1,2}\.\s*(?:janvāra|februāra|marta|aprīļa|maija|jūnija|jūlija|augusta|septembra|oktobra|novembra|decembra|janvāris|februāris|marts|aprīlis|maijs|jūnijs|jūlijs|augusts|septembris|oktobris|novembris|decembris)',
        # Latvian month-only format: "YYYY. gada [month]" (genitive or nominative)
        r'\d{4}\.\s*gada\s+(?:janvāra|februāra|marta|aprīļa|maija|jūnija|jūlija|augusta|septembra|oktobra|novembra|decembra|janvāris|februāris|marts|aprīlis|maijs|jūnijs|jūlijs|augusts|septembris|oktobris|novembris|decembris)',
        # Latvian with dative (used with līdz - until)
        r'\d{4}\.\s*gada\s+\d{1,2}\.\s*(?:janvāram|februāram|martam|aprīlim|maijam|jūnijam|jūlijam|augustam|septembrim|oktobrim|novembrim|decembrim)',
    ]

    # Date range patterns (extract start and end separately)
    DATE_RANGE_PATTERNS = [
        # English: "from DD Month YYYY to DD Month YYYY"
        r'from\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\s+to\s+(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',

        # German: "vom DD. Month YYYY bis zum DD. Month YYYY"
        r'vom\s+(\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4})\s+bis zum\s+(\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4})',

        # Latvian: "no YYYY. gada DD. [month] līdz YYYY. gada DD. [month]"
        r'no\s+(\d{4}\.\s*gada\s+\d{1,2}\.\s*(?:janvāra|februāra|marta|aprīļa|maija|jūnija|jūlija|augusta|septembra|oktobra|novembra|decembra))\s+līdz\s+(\d{4}\.\s*gada\s+\d{1,2}\.\s*(?:janvāram|februāram|martam|aprīlim|maijam|jūnijam|jūlijam|augustam|septembrim|oktobrim|novembrim|decembrim))',
    ]

    # Vague date patterns (multilingual - to detect missing specific values)
    VAGUE_DATE_PATTERNS = [
        # English
        r'in\s+\d+\s+(?:days?|weeks?|months?|years?)',
        r'within\s+\d+\s+(?:days?|weeks?|months?)',
        r'soon',
        r'shortly',
        r'in\s+the\s+near\s+future',
        # German
        r'in\s+\d+\s+(?:Tagen?|Wochen?|Monaten?|Jahren?)',
        r'innerhalb\s+(?:von\s+)?\d+\s+(?:Tagen?|Wochen?|Monaten?)',
        r'bald',
        r'demnächst',
        # Latvian
        r'\d+\s+(?:dienas?|nedēļas?|mēnešos?|gados?)',
        r'drīzumā',
        r'tuvākajā\s+laikā',
    ]

    @classmethod
    def extract_monetary_values(cls, text: str) -> List[MonetaryValue]:
        """Extract monetary values from text."""
        values = []

        for pattern in cls.MONETARY_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()
                    # Parse amount and currency depending on pattern order
                    if pattern == cls.MONETARY_PATTERNS[0]:  # Currency first
                        currency = groups[0]
                        amount_str = groups[1]
                        scale = groups[2] if len(groups) > 2 else ''
                    else:  # Currency last
                        amount_str = groups[0]
                        scale = groups[1] if groups[1] else ''
                        currency = groups[2]

                    # Normalize amount string
                    amount_str = cls._normalize_amount(amount_str)
                    amount = float(amount_str)

                    # Normalize scale
                    scale_normalized = cls._normalize_scale(scale)

                    # Normalize currency
                    currency_normalized = cls._normalize_currency(currency)

                    values.append(MonetaryValue(
                        amount=amount,
                        currency=currency_normalized,
                        original_text=match.group(0),
                        scale=scale_normalized
                    ))
                except (ValueError, IndexError):
                    continue

        return values

    @classmethod
    def _normalize_scale(cls, scale: str) -> str:
        """Normalize scale to standard form."""
        if not scale:
            return ''
        scale_lower = scale.lower()
        if 'billion' in scale_lower or 'mrd' in scale_lower or 'miljardi' in scale_lower:
            return 'billion'
        if 'million' in scale_lower or 'mio' in scale_lower or 'miljonu' in scale_lower:
            return 'million'
        if 'trillion' in scale_lower:
            return 'trillion'
        return scale

    @classmethod
    def _normalize_amount(cls, amount_str: str) -> str:
        """Normalize amount string by resolving thousands/decimal separators."""
        # Remove spaces and non-breaking spaces
        cleaned = (
            amount_str.replace('\u00a0', '')
            .replace('\u202f', '')
            .replace(' ', '')
        )

        has_comma = ',' in cleaned
        has_dot = '.' in cleaned

        if has_comma and has_dot:
            last_comma = cleaned.rfind(',')
            last_dot = cleaned.rfind('.')
            if last_dot > last_comma:
                # Pattern like 1,234.56 -> commas are thousands
                normalized = cleaned.replace(',', '')
            else:
                # Pattern like 1.234,56 -> dots are thousands, comma decimal
                normalized = cleaned.replace('.', '').replace(',', '.')
        elif has_comma:
            parts = cleaned.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                # Single comma with <=2 digits → decimal separator
                normalized = cleaned.replace(',', '.')
            else:
                # Otherwise treat commas as thousands separators
                normalized = cleaned.replace(',', '')
        elif has_dot:
            parts = cleaned.split('.')
            if len(parts) == 2 and len(parts[1]) <= 2:
                normalized = cleaned  # Decimal separator
            else:
                normalized = cleaned.replace('.', '')
        else:
            normalized = cleaned

        return normalized

    @classmethod
    def _normalize_currency(cls, currency: str) -> str:
        """Normalize currency to standard form."""
        currency_map = {
            '€': 'EUR',
            '$': 'USD',
            'eur': 'EUR',
            'euro': 'EUR',
            'euros': 'EUR',
            'eiro': 'EUR',
            'usd': 'USD',
            'gbp': 'GBP',
        }
        return currency_map.get(currency.lower(), currency.upper())

    @classmethod
    def _normalize_legal_type(cls, ref_type: str) -> str:
        """Map extracted legal types to canonical labels."""
        if not ref_type:
            return ''
        return cls.LEGAL_TYPE_NORMALIZATION.get(ref_type.lower(), ref_type.lower())

    @staticmethod
    def _clean_reference_value(value: str) -> str:
        """Trim and standardize a captured legal reference value."""
        if not value:
            return ''

        cleaned = value.replace('\u00a0', ' ').strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.rstrip('.,;')
        return cleaned

    @staticmethod
    def _normalize_ref_value_for_signature(value: str) -> str:
        """Create a compact normalized string for deduplication comparisons."""
        if not value:
            return ''

        compact = re.sub(r'\s+', '', value)
        compact = compact.replace('§', '')
        return compact.lower()

    @classmethod
    def _normalize_reference_signature(cls, ref_type: str, ref_value: str) -> str:
        """Combine canonical type and normalized value for stable equality checks."""
        canonical_type = cls._normalize_legal_type(ref_type)
        normalized_value = cls._normalize_ref_value_for_signature(ref_value)
        if normalized_value:
            return f"{canonical_type}:{normalized_value}"
        return canonical_type

    @staticmethod
    def _semantic_reference_text(reference: LegalReference) -> str:
        """Build a semantic string representation used for embeddings."""
        if reference.reference:
            return f"{reference.type} {reference.reference}".strip()
        return reference.original_text

    @classmethod
    def _get_embedding_generator(cls) -> Optional["EmbeddingGenerator"]:
        """Lazily initialize the embedding generator when available."""
        if cls._embedding_generator_failed:
            return None

        if cls._embedding_generator is None:
            if EmbeddingGenerator is None:
                cls._embedding_generator_failed = True
                return None
            try:
                cls._embedding_generator = EmbeddingGenerator(use_watson=None)
            except Exception:
                cls._embedding_generator_failed = True
                cls._embedding_generator = None
                return None

        return cls._embedding_generator

    @classmethod
    def _compute_embeddings(cls, texts: List[str]) -> Optional[np.ndarray]:
        """Compute embeddings for semantic comparison."""
        generator = cls._get_embedding_generator()
        if generator is None or not texts:
            return None

        try:
            embeddings = generator.generate(texts)
            if embeddings.size == 0:
                return None
            return embeddings
        except Exception:
            cls._embedding_generator_failed = True
            cls._embedding_generator = None
            return None

    @classmethod
    def _merge_reference_group(cls, group: List[LegalReference]) -> LegalReference:
        """Select a representative reference from a semantically similar group."""
        if not group:
            raise ValueError("Cannot merge empty legal reference group")

        # Prefer the reference with the richest original text for context
        primary = max(group, key=lambda ref: len(ref.original_text))
        primary.normalized = cls._normalize_reference_signature(primary.type, primary.reference)
        return primary

    @classmethod
    def _deduplicate_by_normalized_value(cls, references: List[LegalReference]) -> List[LegalReference]:
        """Remove duplicates based on normalized signatures while preserving order."""
        unique: Dict[str, LegalReference] = {}
        ordered: List[LegalReference] = []

        for ref in references:
            signature = ref.normalized or cls._normalize_reference_signature(ref.type, ref.reference)
            if signature not in unique:
                ref.normalized = signature
                unique[signature] = ref
                ordered.append(ref)

        return ordered

    @classmethod
    def _deduplicate_semantically_equivalent(cls, references: List[LegalReference]) -> List[LegalReference]:
        """Group legal references that are semantically equivalent across translations."""
        if len(references) <= 1:
            return cls._deduplicate_by_normalized_value(references)

        semantic_texts = [cls._semantic_reference_text(ref) for ref in references]
        embeddings = cls._compute_embeddings(semantic_texts)

        if embeddings is None or embeddings.shape[0] != len(references):
            return cls._deduplicate_by_normalized_value(references)

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0.0, 1.0, norms)
        normalized_embeddings = embeddings / norms

        used_indices = set()
        deduped: List[LegalReference] = []

        for idx, reference in enumerate(references):
            if idx in used_indices:
                continue

            group_indices = [idx]
            used_indices.add(idx)

            for candidate_idx in range(idx + 1, len(references)):
                if candidate_idx in used_indices:
                    continue
                if references[candidate_idx].type != reference.type:
                    continue

                similarity = float(np.dot(normalized_embeddings[idx], normalized_embeddings[candidate_idx]))
                if similarity >= cls.LEGAL_SIMILARITY_THRESHOLD:
                    used_indices.add(candidate_idx)
                    group_indices.append(candidate_idx)

            group = [references[i] for i in group_indices]
            deduped.append(cls._merge_reference_group(group))

        return cls._deduplicate_by_normalized_value(deduped)

    @classmethod
    def extract_legal_references(cls, text: str) -> List[LegalReference]:
        """Extract legal references from text."""
        references: List[LegalReference] = []

        for ref_type, patterns in cls.LEGAL_PATTERNS.items():
            canonical_type = cls._normalize_legal_type(ref_type)

            for pattern in patterns:
                for match in pattern.finditer(text):
                    group_dict = match.groupdict()
                    if group_dict and 'ref' in group_dict:
                        raw_value = group_dict['ref']
                    elif match.groups():
                        raw_value = match.group(1)
                    else:
                        raw_value = match.group(0)

                    cleaned_value = cls._clean_reference_value(raw_value)
                    normalized_signature = cls._normalize_reference_signature(canonical_type, cleaned_value)

                    references.append(LegalReference(
                        type=canonical_type,
                        reference=cleaned_value,
                        original_text=match.group(0),
                        normalized=normalized_signature
                    ))

        expanded = cls._expand_article_references(references)
        return cls._deduplicate_semantically_equivalent(expanded)

    @classmethod
    def _expand_article_references(cls, references: List[LegalReference]) -> List[LegalReference]:
        """
        Split article references that include paragraph notation (e.g., Article 6(2))
        into separate article and paragraph references so we can align them with
        languages that spell out the paragraph explicitly (e.g., Artikel 6 Absatz 2).
        """
        expanded: List[LegalReference] = []

        for ref in references:
            if ref.type != 'article':
                expanded.append(ref)
                continue

            match = re.match(
                r'(?P<base>\d+[a-z]?)(?P<suffix>(\([0-9a-z]+\))+)$',
                ref.reference,
                re.IGNORECASE
            )

            if not match:
                expanded.append(ref)
                continue

            base = match.group('base')
            suffix = match.group('suffix')

            # Always include the base article reference
            base_ref = LegalReference(
                type='article',
                reference=base,
                original_text=ref.original_text,
                normalized=cls._normalize_reference_signature('article', base)
            )
            expanded.append(base_ref)

            # Extract paragraph / sub-paragraph components from parentheses
            inner_values = re.findall(r'\(([0-9a-z]+)\)', suffix, flags=re.IGNORECASE)
            for value in inner_values:
                paragraph_ref = LegalReference(
                    type='paragraph',
                    reference=value,
                    original_text=ref.original_text,
                    normalized=cls._normalize_reference_signature('paragraph', value)
                )
                expanded.append(paragraph_ref)

        return expanded

    @classmethod
    def _normalize_date_string(cls, date_str: str) -> str:
        """
        Replace German/Latvian month names with English equivalents for parsing.
        Also cleans up common prepositions and formatting.
        """
        normalized = date_str.strip()

        # Remove common prepositions that interfere with parsing
        normalized = re.sub(r'^(vom|im|no)\s+', '', normalized, flags=re.IGNORECASE)

        # Replace foreign month names with English
        for foreign_month, english_month in cls.MONTH_NAMES.items():
            # Use word boundaries to avoid partial matches
            normalized = re.sub(
                r'\b' + re.escape(foreign_month) + r'\b',
                english_month,
                normalized,
                flags=re.IGNORECASE
            )

        # Handle Latvian format: "YYYY. gada DD. month" -> "DD month YYYY"
        latvian_match = re.match(
            r'(\d{4})\.\s*gada\s+(\d{1,2})\.\s*(\w+)',
            normalized,
            re.IGNORECASE
        )
        if latvian_match:
            year, day, month = latvian_match.groups()
            normalized = f"{day} {month} {year}"

        # Handle Latvian month-only: "YYYY. gada month" -> "month YYYY"
        latvian_month_only = re.match(
            r'(\d{4})\.\s*gada\s+(\w+)',
            normalized,
            re.IGNORECASE
        )
        if latvian_month_only:
            year, month = latvian_month_only.groups()
            normalized = f"1 {month} {year}"  # Default to 1st of month

        return normalized

    @classmethod
    def extract_dates(cls, text: str) -> List[DateValue]:
        """Extract dates from text."""
        dates = []
        seen_positions = set()  # Track text positions to avoid duplicates

        # Check for vague dates first
        for pattern in cls.VAGUE_DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.start() not in seen_positions:
                    dates.append(DateValue(
                        date=None,
                        original_text=match.group(0),
                        is_vague=True
                    ))
                    seen_positions.add(match.start())

        # Extract date ranges first (they contain multiple dates)
        for pattern in cls.DATE_RANGE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Mark entire range as seen to avoid re-extracting individual dates
                for pos in range(match.start(), match.end()):
                    seen_positions.add(pos)

                # Extract start and end dates from the range
                if match.groups() and len(match.groups()) >= 2:
                    start_date_str = match.group(1)
                    end_date_str = match.group(2)

                    # Parse start date
                    try:
                        normalized_start = cls._normalize_date_string(start_date_str)
                        parsed_start = date_parser.parse(normalized_start, dayfirst=True)
                        dates.append(DateValue(
                            date=parsed_start,
                            original_text=start_date_str,
                            is_vague=False
                        ))
                    except (ValueError, TypeError):
                        dates.append(DateValue(
                            date=None,
                            original_text=start_date_str,
                            is_vague=False
                        ))

                    # Parse end date
                    try:
                        normalized_end = cls._normalize_date_string(end_date_str)
                        parsed_end = date_parser.parse(normalized_end, dayfirst=True)
                        dates.append(DateValue(
                            date=parsed_end,
                            original_text=end_date_str,
                            is_vague=False
                        ))
                    except (ValueError, TypeError):
                        dates.append(DateValue(
                            date=None,
                            original_text=end_date_str,
                            is_vague=False
                        ))

        # Extract specific dates (skip if already part of a range)
        for pattern in cls.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Skip if this date overlaps with an already-extracted range
                if match.start() in seen_positions:
                    continue

                date_str = match.group(0)
                seen_positions.add(match.start())

                try:
                    # Normalize German/Latvian dates to English
                    normalized_date = cls._normalize_date_string(date_str)
                    # Try to parse the normalized date
                    parsed_date = date_parser.parse(normalized_date, dayfirst=True)
                    dates.append(DateValue(
                        date=parsed_date,
                        original_text=date_str,
                        is_vague=False
                    ))
                except (ValueError, TypeError):
                    # If parsing fails, still record it
                    dates.append(DateValue(
                        date=None,
                        original_text=date_str,
                        is_vague=False
                    ))

        return dates

    @classmethod
    def extract_all(cls, text: str) -> Dict[str, List]:
        """Extract all entity types from text."""
        return {
            'monetary': cls.extract_monetary_values(text),
            'legal': cls.extract_legal_references(text),
            'dates': cls.extract_dates(text)
        }


if __name__ == "__main__":
    # Test the extractor
    test_text = """
    The facility is supported with EUR 1,500 million and a maximum of
    1.5 Mrd. USD in loans. According to Regulation (EU) 2021/947 Article 19(2),
    decisions shall be adopted by 30/06/2029 or in 2 weeks.
    See also case C-785/22 P and ECLI:EU:C:2024:52.
    """

    extractor = EntityExtractor()
    results = extractor.extract_all(test_text)

    print("Monetary values:")
    for val in results['monetary']:
        print(f"  {val}")

    print("\nLegal references:")
    for ref in results['legal']:
        print(f"  {ref}")

    print("\nDates:")
    for date in results['dates']:
        print(f"  {date}")
