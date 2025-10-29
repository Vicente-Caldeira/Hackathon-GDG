"""
Extract entities from text: dates, monetary values, legal references, etc.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from dateutil import parser as date_parser
from datetime import datetime


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
    MONETARY_PATTERNS = [
        # EUR 1500 million, EUR 1,500 million, etc.
        r'(EUR|USD|GBP|€|\$)\s*([0-9]{1,3}(?:[,.\s][0-9]{3})*(?:[,.][0-9]+)?)\s*(million|billion|trillion|Mio\.|Mrd\.|miljonu|miljardi)?',
        # 1500 million EUR, 1,5 Mrd. EUR, etc.
        r'([0-9]{1,3}(?:[,.\s][0-9]{3})*(?:[,.][0-9]+)?)\s*(million|billion|trillion|Mio\.|Mrd\.|miljonu|miljardi)?\s*(EUR|USD|GBP|€|\$)',
    ]

    # Legal reference patterns (multilingual)
    LEGAL_PATTERNS = {
        'regulation': r'\(EU,?\s*Euratom?\)\s*(?:No\.?|Nr\.?|regulas\s*Nr\.?)?\s*([0-9]+/[0-9]+)',
        'regulation_short': r'\(E[USR],?\s*Euratom?\)\s*([0-9]+/[0-9]+)',
        # English: Article, German: Artikel, Latvian: pants
        'article': r'(?:Art(?:icle|ikel)?|pants)\.?\s*([0-9]+(?:\([0-9]+\))?(?:\s*[a-z])?)',
        # English: Paragraph, German: Absatz, Latvian: rindkopa
        'paragraph': r'(?:Paragraph|Absatz|rindkopa)\s*([0-9]+)',
        'case': r'([CT][-‑][0-9]+/[0-9]+\s*P?)',
        'ecli': r'(E[CU]LI?:[A-Z]+:[0-9]{4}:[0-9]+)',
    }

    # Date patterns (multilingual)
    DATE_PATTERNS = [
        r'\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}',  # 16/06/2023, 2023-06-16
        r'\d{4}[-‑]\d{2}[-‑]\d{2}',             # 2023-06-16
        # English months
        r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        # German months
        r'\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4}',
        # Latvian months
        r'\d{1,2}\.\s*(?:janvāris|februāris|marts|aprīlis|maijs|jūnijs|jūlijs|augusts|septembris|oktobris|novembris|decembris)\s+\d{4}',
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
                    amount_str = amount_str.replace(',', '.').replace(' ', '')
                    # Handle formats like "1.500" (European) vs "1,500" (US)
                    if '.' in amount_str and amount_str.count('.') == 1:
                        parts = amount_str.split('.')
                        if len(parts[1]) == 3:  # Likely thousand separator
                            amount_str = amount_str.replace('.', '')

                    amount = float(amount_str.replace(',', ''))

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
    def _normalize_currency(cls, currency: str) -> str:
        """Normalize currency to standard form."""
        currency_map = {
            '€': 'EUR',
            '$': 'USD',
            'eur': 'EUR',
            'usd': 'USD',
            'gbp': 'GBP',
        }
        return currency_map.get(currency.lower(), currency.upper())

    @classmethod
    def extract_legal_references(cls, text: str) -> List[LegalReference]:
        """Extract legal references from text."""
        references = []

        for ref_type, pattern in cls.LEGAL_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                references.append(LegalReference(
                    type=ref_type,
                    reference=match.group(1) if match.groups() else match.group(0),
                    original_text=match.group(0)
                ))

        return references

    @classmethod
    def extract_dates(cls, text: str) -> List[DateValue]:
        """Extract dates from text."""
        dates = []

        # Check for vague dates first
        for pattern in cls.VAGUE_DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                dates.append(DateValue(
                    date=None,
                    original_text=match.group(0),
                    is_vague=True
                ))

        # Extract specific dates
        for pattern in cls.DATE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(0)
                try:
                    # Try to parse the date
                    parsed_date = date_parser.parse(date_str, dayfirst=True)
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
