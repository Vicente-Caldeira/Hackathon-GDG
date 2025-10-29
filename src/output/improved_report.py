"""
Generate improved Excel report matching the expected format.
Shows actual entity values instead of PRESENT/MISSING labels.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from pathlib import Path
from typing import List, Dict
from collections import defaultdict

from src.validators.consistency_checker import Difference
from src.loaders.json_loader import Document
from src.extractors.entity_extractor import EntityExtractor
from config import OUTPUT_DIR


class ImprovedReportGenerator:
    """Generate human-readable reports with actual values."""

    def __init__(self):
        self.extractor = EntityExtractor()

    def generate_excel_with_values(
        self,
        differences: List[Difference],
        documents: Dict[str, Document],
        output_file: Path = None
    ) -> Path:
        """
        Generate Excel report showing actual entity values.

        Args:
            differences: List of detected differences
            documents: Original documents to extract full text from
            output_file: Output file path

        Returns:
            Path to generated file
        """
        if output_file is None:
            output_file = OUTPUT_DIR / "differences.xlsx"

        # Group differences by paragraph
        by_paragraph = defaultdict(list)
        for diff in differences:
            # Use EN paragraph as primary key
            para_id = diff.paragraph_ids.get('en') or diff.paragraph_ids.get('de') or diff.paragraph_ids.get('lv')
            if para_id is not None:
                by_paragraph[para_id].append(diff)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inconsistencies"

        # Define styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")

        # Headers matching expected format
        headers = ["Paragraph", "EN", "DE", "LV"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        # Add summary rows
        row_num = 2
        ws.cell(row=row_num, column=1, value="REGULATION").font = Font(bold=True)
        row_num += 1
        ws.cell(row=row_num, column=1, value="Date").font = Font(bold=True)
        row_num += 1

        # Process differences by paragraph
        for para_id in sorted(by_paragraph.keys()):
            diffs = by_paragraph[para_id]

            # For each difference, show the actual values
            for diff in diffs:
                values = diff.values

                # Extract actual values (not "PRESENT"/"MISSING")
                en_val = values.get('en', '')
                de_val = values.get('de', '')
                lv_val = values.get('lv', '')

                # Skip if all are generic labels
                if en_val in ['PRESENT', 'MISSING'] and de_val in ['PRESENT', 'MISSING'] and lv_val in ['PRESENT', 'MISSING']:
                    continue

                # Convert "MISSING" to empty string for cleaner display
                if en_val == "MISSING":
                    en_val = ""
                if de_val == "MISSING":
                    de_val = ""
                if lv_val == "MISSING":
                    lv_val = ""

                # Write row
                ws.cell(row=row_num, column=1, value=f"({para_id})")
                ws.cell(row=row_num, column=2, value=en_val)
                ws.cell(row=row_num, column=3, value=de_val)
                ws.cell(row=row_num, column=4, value=lv_val)

                row_num += 1

        # Adjust column widths
        ws.column_dimensions['A'].width = 15
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 35
        ws.column_dimensions['D'].width = 35

        # Freeze header row
        ws.freeze_panes = "A2"

        wb.save(output_file)
        print(f"✓ Improved Excel report saved to: {output_file}")
        return output_file


if __name__ == "__main__":
    # Test with actual data
    from src.loaders.json_loader import JSONLoader
    from src.alignment.simple_aligner import SimpleAligner
    from src.validators.consistency_checker import ConsistencyChecker
    from config import INPUT_FILES

    print("Loading documents...")
    documents = JSONLoader.load_all(INPUT_FILES)

    print("Aligning paragraphs...")
    aligner = SimpleAligner()
    aligned = aligner.align_documents(documents)

    print("Checking consistency...")
    checker = ConsistencyChecker()
    differences = checker.check_all(aligned)

    print(f"Found {len(differences)} differences")

    print("Generating improved report...")
    generator = ImprovedReportGenerator()
    generator.generate_excel_with_values(differences, documents)

    print("Done!")
