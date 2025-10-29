"""
Simple paragraph alignment by paragraph number (for pre-aligned documents).
"""
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.loaders.json_loader import Document, Paragraph


@dataclass
class AlignedParagraphs:
    """Represents aligned paragraphs across languages."""
    en: Optional[Paragraph]
    de: Optional[Paragraph]
    lv: Optional[Paragraph]

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


class SimpleAligner:
    """Simple alignment based on paragraph index (assumes documents are pre-aligned)."""

    @staticmethod
    def align_documents(documents: Dict[str, Document]) -> List[AlignedParagraphs]:
        """
        Align paragraphs by index, detecting missing paragraphs.

        Args:
            documents: Dictionary mapping language codes to Document objects

        Returns:
            List of AlignedParagraphs objects (with None for missing paragraphs)
        """
        en_doc = documents['en']
        de_doc = documents['de']
        lv_doc = documents['lv']

        # Find the maximum length to detect all structural differences
        max_len = max(len(en_doc), len(de_doc), len(lv_doc))

        aligned = []
        for i in range(max_len):
            # None if paragraph doesn't exist in this language
            para_en = en_doc.paragraphs[i] if i < len(en_doc) else None
            para_de = de_doc.paragraphs[i] if i < len(de_doc) else None
            para_lv = lv_doc.paragraphs[i] if i < len(lv_doc) else None

            aligned.append(AlignedParagraphs(
                en=para_en,
                de=para_de,
                lv=para_lv
            ))

        return aligned


if __name__ == "__main__":
    from config import INPUT_FILES
    from src.loaders.json_loader import JSONLoader

    print("Loading documents...")
    documents = JSONLoader.load_all(INPUT_FILES)

    print("\nAligning paragraphs...")
    aligner = SimpleAligner()
    aligned = aligner.align_documents(documents)

    print(f"\n✓ Aligned {len(aligned)} paragraph groups")

    # Count missing paragraphs
    missing_count = sum(1 for g in aligned if not g.has_all_languages())
    if missing_count > 0:
        print(f"⚠ Warning: {missing_count} groups have missing paragraphs")

    print("\nFirst 5 alignments:")
    for i, group in enumerate(aligned[:5]):
        print(f"{i+1}. {group}")
        if group.has_all_languages():
            print(f"   EN: {group.en.text[:60]}...")
            print(f"   DE: {group.de.text[:60]}...")
            print(f"   LV: {group.lv.text[:60]}...")
        else:
            print(f"   ⚠ Missing languages detected!")
            if group.en:
                print(f"   EN: {group.en.text[:60]}...")
            if group.de:
                print(f"   DE: {group.de.text[:60]}...")
            if group.lv:
                print(f"   LV: {group.lv.text[:60]}...")
