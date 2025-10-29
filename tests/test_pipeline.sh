#!/bin/bash
# Comprehensive test script for the document consistency checker

set -e  # Exit on error

echo "=========================================="
echo "Document Consistency Checker - Test Suite"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Smoke test (imports)
echo ""
echo "Test 1: Module Imports"
echo "----------------------"
if python3 tests/test_imports.py; then
    echo -e "${GREEN}✓ All modules imported successfully${NC}"
else
    echo -e "${RED}✗ Import test failed${NC}"
    exit 1
fi

# Test 2: Simple alignment
echo ""
echo "Test 2: Simple Alignment (Rule-based)"
echo "--------------------------------------"
if python3 main.py --format json 2>&1 | grep -q "Processing complete"; then
    echo -e "${GREEN}✓ Simple alignment completed${NC}"

    # Check output files
    if [ -f "output/differences.json" ]; then
        DIFF_COUNT=$(python3 -c "import json; data=json.load(open('output/differences.json')); print(len(data.get('differences', [])))")
        echo -e "${GREEN}  Found ${DIFF_COUNT} differences${NC}"
    fi
else
    echo -e "${RED}✗ Simple alignment failed${NC}"
    exit 1
fi

# Test 3: Test individual components
echo ""
echo "Test 3: Component Tests"
echo "-----------------------"

# Test JSON loader
echo -n "  Testing JSON loader... "
if python3 -c "
from src.loaders.json_loader import JSONLoader
from config import INPUT_FILES
docs = JSONLoader.load_all(INPUT_FILES)
assert len(docs) == 3, 'Should load 3 languages'
assert 'en' in docs and 'de' in docs and 'lv' in docs
print(f'Loaded: EN={len(docs[\"en\"])} DE={len(docs[\"de\"])} LV={len(docs[\"lv\"])} paragraphs')
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test entity extractor
echo -n "  Testing entity extractor... "
if python3 -c "
from src.extractors.entity_extractor import EntityExtractor
extractor = EntityExtractor()
EntityExtractor._embedding_generator_failed = True
text = 'The facility is supported with EUR 520 million on 16/06/2023.'
entities = extractor.extract_all(text)
assert len(entities['monetary']) > 0, 'Should extract monetary value'
assert len(entities['dates']) > 0, 'Should extract date'
formats = [
    ('EUR 1,234.56 grant', 1234.56),
    ('Budget: 1.234,56 EUR', 1234.56),
]
for sample, expected in formats:
    values = EntityExtractor.extract_monetary_values(sample)
    assert values, f'Monetary value missing for {sample}'
    assert abs(values[0].amount - expected) < 1e-6, f'Incorrect amount for {sample}: {values[0].amount}'
legal_samples = [
    ('Article 6(2)', {'article': {'6'}, 'paragraph': {'2'}}),
    ('Artikel 6 Absatz 2', {'article': {'6'}, 'paragraph': {'2'}}),
    ('6. panta 2. punkta', {'article': {'6'}, 'paragraph': {'2'}}),
]
for sample, expected in legal_samples:
    refs = EntityExtractor.extract_legal_references(sample)
    article_refs = {r.reference for r in refs if r.type == 'article'}
    paragraph_refs = {r.reference for r in refs if r.type == 'paragraph'}
    assert expected['article'].issubset(article_refs), f'Missing article ref in \"{sample}\"'
    assert expected['paragraph'].issubset(paragraph_refs), f'Missing paragraph ref in \"{sample}\"'
print(f'Extracted: {len(entities[\"monetary\"])} monetary, {len(entities[\"dates\"])} dates')
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test embeddings (local only)
echo -n "  Testing local embeddings... "
if python3 -c "
from src.alignment.embeddings import EmbeddingGenerator
gen = EmbeddingGenerator(use_watson=False)
emb = gen.generate(['test sentence'])
assert emb.shape[0] == 1, 'Should generate 1 embedding'
print(f'Generated embedding: shape={emb.shape}')
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test simple aligner
echo -n "  Testing simple aligner... "
if python3 -c "
from src.loaders.json_loader import JSONLoader
from src.alignment.simple_aligner import SimpleAligner
from config import INPUT_FILES
docs = JSONLoader.load_all(INPUT_FILES)
aligner = SimpleAligner()
aligned = aligner.align_documents(docs)
print(f'Aligned {len(aligned)} paragraph groups')
assert len(aligned) > 0, 'Should produce alignments'
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test consistency checker
echo -n "  Testing consistency checker... "
if python3 -c "
from src.loaders.json_loader import JSONLoader
from src.alignment.simple_aligner import SimpleAligner
from src.validators.consistency_checker import ConsistencyChecker
from config import INPUT_FILES
docs = JSONLoader.load_all(INPUT_FILES)
aligner = SimpleAligner()
aligned = aligner.align_documents(docs)
checker = ConsistencyChecker()
diffs = checker.check_all(aligned)
print(f'Found {len(diffs)} differences')
assert isinstance(diffs, list), 'Should return list'
" 2>&1; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
fi

# Test 4: Cache system
echo ""
echo "Test 4: Cache System"
echo "--------------------"
echo "  Checking cache directory..."
if [ -d ".cache" ]; then
    echo -e "${GREEN}  ✓ Cache directory exists${NC}"
    CACHE_FILES=$(ls -1 .cache/*.npz 2>/dev/null | wc -l)
    echo "    Cache files: $CACHE_FILES"
else
    echo -e "${YELLOW}  ⚠ Cache directory not yet created${NC}"
fi

# Test 5: Output validation
echo ""
echo "Test 5: Output Validation"
echo "-------------------------"
if [ -f "output/differences.json" ]; then
    echo -n "  Validating JSON output... "
    if python3 -c "import json; json.load(open('output/differences.json'))" 2>&1; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗ Invalid JSON${NC}"
    fi
fi

if [ -f "output/differences.xlsx" ]; then
    echo -e "${GREEN}  ✓ Excel output exists${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo "Test Suite Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review output files in output/"
echo "  2. Run semantic alignment: python3 main.py --semantic --local"
echo "  3. Compare results between simple and semantic modes"
echo ""
