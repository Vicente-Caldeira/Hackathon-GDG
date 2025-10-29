#!/usr/bin/env python3
"""
Run the document consistency checker on the NEW evaluation dataset.
"""
import argparse
from pathlib import Path

from src.loaders.json_loader import JSONLoader
from src.alignment.simple_aligner import SimpleAligner
from src.alignment.paragraph_aligner import ParagraphAligner
from src.alignment.embeddings import EmbeddingGenerator
from src.validators.consistency_checker import ConsistencyChecker
from src.output.report_generator import ReportGenerator


# New dataset files
INPUT_FILES_NEW = {
    "en": Path("datanew/eval_sample_en.json"),
    "de": Path("datanew/eval_sample_de.json"),
    "lv": Path("datanew/eval_sample_lv.json")
}

OUTPUT_DIR = Path("output")


def main(output_format: str = "both", use_semantic: bool = False, use_watson: bool = None):
    """
    Main execution flow for NEW evaluation dataset.
    """
    print("=" * 70)
    print("Document Consistency Checker - NEW EVALUATION DATASET")
    print("=" * 70)

    # Step 1: Load documents
    print("\n[1/4] Loading NEW evaluation documents...")
    documents = JSONLoader.load_all(INPUT_FILES_NEW)
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

    # Step 4: Generate reports with _eval suffix
    print("\n[4/4] Generating reports...")
    report_gen = ReportGenerator()

    if output_format in ['json', 'both']:
        output_path = OUTPUT_DIR / "differences_eval.json"
        report_gen.generate_json(differences, output_path=output_path)

    if output_format in ['excel', 'both']:
        output_path = OUTPUT_DIR / "differences_eval.xlsx"
        report_gen.generate_excel(differences, output_path=output_path)

    # Print summary
    print("\n" + report_gen.generate_summary(differences))

    print("\n" + "=" * 70)
    print("✓ Processing complete!")
    print(f"  Output files:")
    print(f"    - output/differences_eval.json")
    print(f"    - output/differences_eval.xlsx")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check consistency on NEW evaluation dataset"
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
        help="Use semantic embedding-based alignment"
    )
    parser.add_argument(
        "--watson",
        action='store_true',
        help="Force use of Watson AI embeddings"
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

    main(
        output_format=args.format,
        use_semantic=args.semantic,
        use_watson=use_watson
    )
