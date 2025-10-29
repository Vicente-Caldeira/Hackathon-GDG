#!/usr/bin/env python3
"""
Document Consistency Checker - IBM Hackathon Project
Main entry point for the application.
"""
import argparse
from pathlib import Path

from config import INPUT_FILES, OUTPUT_DIR
from src.loaders.json_loader import JSONLoader
from src.alignment.simple_aligner import SimpleAligner
from src.validators.consistency_checker import ConsistencyChecker
from src.output.report_generator import ReportGenerator


def main(output_format: str = "both"):
    """
    Main execution flow.

    Args:
        output_format: Output format ('json', 'excel', or 'both')
    """
    print("=" * 70)
    print("  Document Consistency Checker - IBM Hackathon")
    print("=" * 70)

    # Step 1: Load documents
    print("\n[1/4] Loading documents...")
    documents = JSONLoader.load_all(INPUT_FILES)
    for lang, doc in documents.items():
        print(f"  ✓ {lang.upper()}: {len(doc)} paragraphs")

    # Step 2: Align paragraphs (simple index-based alignment)
    print("\n[2/4] Aligning paragraphs across languages...")
    aligner = SimpleAligner()
    aligned = aligner.align_documents(documents)
    print(f"  ✓ Aligned {len(aligned)} paragraph groups")

    # Step 3: Check consistency
    print("\n[3/4] Checking for inconsistencies...")
    checker = ConsistencyChecker()
    differences = checker.check_all(aligned)
    print(f"  ✓ Found {len(differences)} differences")

    # Step 4: Generate reports
    print("\n[4/4] Generating reports...")
    report_gen = ReportGenerator()

    if output_format in ['json', 'both']:
        report_gen.generate_json(differences)

    if output_format in ['excel', 'both']:
        report_gen.generate_excel(differences)

    # Print summary
    print("\n" + report_gen.generate_summary(differences))

    print("\n" + "=" * 70)
    print("✓ Processing complete!")
    print(f"  Output directory: {OUTPUT_DIR.absolute()}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check consistency across multilingual legal documents"
    )
    parser.add_argument(
        "--format",
        choices=['json', 'excel', 'both'],
        default='both',
        help="Output format (default: both)"
    )

    args = parser.parse_args()

    main(output_format=args.format)
