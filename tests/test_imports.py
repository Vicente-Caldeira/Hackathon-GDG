#!/usr/bin/env python3
"""
Smoke test: Verify all modules can be imported without errors.
This catches missing dependencies, circular imports, and syntax errors.
"""
import sys
import importlib
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_module_imports():
    """Test that all core modules can be imported."""
    modules = [
        # Config
        'config',

        # Loaders
        'src.loaders.json_loader',

        # Alignment
        'src.alignment.embeddings',
        'src.alignment.simple_aligner',
        'src.alignment.paragraph_aligner',

        # Extractors
        'src.extractors.entity_extractor',

        # Validators
        'src.validators.consistency_checker',

        # Output
        'src.output.report_generator',
    ]

    failed = []

    for module_name in modules:
        try:
            importlib.import_module(module_name)
            print(f"✓ {module_name}")
        except Exception as e:
            print(f"✗ {module_name}: {e}")
            failed.append((module_name, str(e)))

    if failed:
        print(f"\n❌ {len(failed)} module(s) failed to import:")
        for module, error in failed:
            print(f"  - {module}: {error}")
        sys.exit(1)
    else:
        print(f"\n✅ All {len(modules)} modules imported successfully")
        sys.exit(0)


if __name__ == "__main__":
    test_module_imports()
