"""
Simple paragraph alignment by paragraph number (for pre-aligned documents).
"""
from typing import Dict, List
from dataclasses import dataclass

from src.loaders.json_loader import Document, Paragraph


@dataclass
class AlignedParagraphs:
    """Represents aligned paragraphs across languages."""
    en: Paragraph
    de: Paragraph
    lv: Paragraph

    def get_paragraph_ids(self) -> Dict[str, int]:
        """Get paragraph numbers for each language."""
        return {
            'en': self.en.para_number,
            'de': self.de.para_number,
            'lv': self.lv.para_number
        }

    def has_all_languages(self) -> bool:
        """Check if all three languages are present."""
        return True  # Always true for this simple aligner

    def __repr__(self):
        ids = self.get_paragraph_ids()
        return f"Aligned(EN:{ids['en']}, DE:{ids['de']}, LV:{ids['lv']})"


class SimpleAligner:
    """Simple alignment based on paragraph index (assumes documents are pre-aligned)."""

    @staticmethod
    def align_documents(documents: Dict[str, Document]) -> List[AlignedParagraphs]:
        """
        Align paragraphs by index.

        Args:
            documents: Dictionary mapping language codes to Document objects

        Returns:
            List of AlignedParagraphs objects
        """
        en_doc = documents['en']
        de_doc = documents['de']
        lv_doc = documents['lv']

        # Find the minimum length
        min_len = min(len(en_doc), len(de_doc), len(lv_doc))

        aligned = []
        for i in range(min_len):
            aligned.append(AlignedParagraphs(
                en=en_doc.paragraphs[i],
                de=de_doc.paragraphs[i],
                lv=lv_doc.paragraphs[i]
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
    print("\nFirst 5 alignments:")
    for i, group in enumerate(aligned[:5]):
        print(f"{i+1}. {group}")
        print(f"   EN: {group.en.text[:60]}...")
        print(f"   DE: {group.de.text[:60]}...")
        print(f"   LV: {group.lv.text[:60]}...")
