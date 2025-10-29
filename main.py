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
from src.alignment.paragraph_aligner import ParagraphAligner
from src.alignment.embeddings import EmbeddingGenerator
from src.validators.consistency_checker import ConsistencyChecker
from src.output.report_generator import ReportGenerator


def main(output_format: str = "both", use_semantic: bool = False, use_watson: bool = None):
    """
    Main execution flow.

    Args:
        output_format: Output format ('json', 'excel', or 'both')
        use_semantic: Use semantic embedding-based alignment instead of simple index-based
        use_watson: Use Watson AI embeddings (None = auto-detect, True = force Watson, False = force local)
    """
    print("=" * 70)
    print("Document Consistency Checker")
    print("=" * 70)

    # Step 1: Load documents
    print("\n[1/4] Loading documents...")
    documents = JSONLoader.load_all(INPUT_FILES)
    for lang, doc in documents.items():
        print(f"  ✓ {lang.upper()}: {len(doc)} paragraphs")

    # Step 2: Align paragraphs
    print("\n[2/4] Aligning paragraphs across languages...")
    if use_semantic:
        print("  → Using semantic embedding-based alignment")
        embedding_gen = EmbeddingGenerator(use_watson=use_watson)
        aligner = ParagraphAligner(embedding_gen)
        aligned = aligner.align_documents(documents, use_cache=True)
    else:
        print("  → Using simple index-based alignment")
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
    parser.add_argument(
        "--semantic",
        action='store_true',
        help="Use semantic embedding-based alignment instead of simple index-based"
    )
    parser.add_argument(
        "--watson",
        action='store_true',
        help="Force use of Watson AI embeddings (requires credentials)"
    )
    parser.add_argument(
        "--local",
        action='store_true',
        help="Force use of local embeddings model"
    )

    args = parser.parse_args()

    # Determine watson flag
    use_watson = None
    if args.watson:
        use_watson = True
    elif args.local:
        use_watson = False

    main(output_format=args.format, use_semantic=args.semantic, use_watson=use_watson)
