"""
Load and parse JSON files from the provided parsed documents.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Paragraph:
    """Represents a single paragraph from a document."""
    text: str
    para_number: int
    language: str

    def __repr__(self):
        preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"Paragraph(#{self.para_number}, lang={self.language}, text='{preview}')"


@dataclass
class Document:
    """Represents a loaded document with all its paragraphs."""
    filename: str
    language: str
    paragraphs: List[Paragraph]

    def __len__(self):
        return len(self.paragraphs)

    def get_paragraph(self, para_number: int) -> Optional[Paragraph]:
        """Get paragraph by its number."""
        for para in self.paragraphs:
            if para.para_number == para_number:
                return para
        return None

    def __repr__(self):
        return f"Document(lang={self.language}, paragraphs={len(self.paragraphs)})"


class JSONLoader:
    """Loads parsed JSON documents."""

    @staticmethod
    def load(file_path: Path, language: str) -> Document:
        """
        Load a parsed JSON file.

        Args:
            file_path: Path to the JSON file
            language: Language code (en, de, lv)

        Returns:
            Document object containing all paragraphs
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # The JSON structure is: [{"file": "...", "para": [...]}]
        if not data or not isinstance(data, list):
            raise ValueError(f"Invalid JSON structure in {file_path}")

        doc_data = data[0]
        filename = doc_data.get("file", "")
        para_list = doc_data.get("para", [])

        paragraphs = []
        for para_data in para_list:
            para = Paragraph(
                text=para_data.get("para", "").strip(),
                para_number=para_data.get("para_number", 0),
                language=language
            )
            paragraphs.append(para)

        return Document(
            filename=filename,
            language=language,
            paragraphs=paragraphs
        )

    @staticmethod
    def load_all(file_paths: Dict[str, Path]) -> Dict[str, Document]:
        """
        Load all documents.

        Args:
            file_paths: Dictionary mapping language codes to file paths

        Returns:
            Dictionary mapping language codes to Document objects
        """
        documents = {}
        for lang, path in file_paths.items():
            documents[lang] = JSONLoader.load(path, lang)
        return documents


if __name__ == "__main__":
    # Test the loader
    from config import INPUT_FILES

    print("Testing JSON loader...")
    docs = JSONLoader.load_all(INPUT_FILES)

    for lang, doc in docs.items():
        print(f"\n{lang.upper()}: {doc}")
        print(f"  First paragraph: {doc.paragraphs[0]}")
        print(f"  Last paragraph: {doc.paragraphs[-1]}")
