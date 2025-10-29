# Technical Details & Implementation Guide

Complete technical documentation for the Document Consistency Checker.

---

## Table of Contents

1. [Architecture](#architecture)
2. [All Fixes Applied (23)](#all-fixes-applied)
3. [Testing Guide](#testing-guide)
4. [Watson AI Setup](#watson-ai-setup)
5. [Implementation Approach](#implementation-approach)
6. [Optimization Work](#optimization-work)

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                    (CLI Entry Point)                         │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
    ▼            ▼            ▼
┌────────┐  ┌─────────┐  ┌────────────┐
│ Loader │  │ Aligner │  │ Validator  │
└────────┘  └─────────┘  └────────────┘
                 │
         ┌───────┴───────┐
         │               │
         ▼               ▼
    ┌────────┐    ┌──────────┐
    │ Simple │    │ Semantic │
    │ Align  │    │  Align   │
    └────────┘    └──────────┘
                       │
                       ▼
                 ┌──────────┐
                 │Embeddings│
                 └──────────┘
                       │
              ┌────────┴────────┐
              │                 │
              ▼                 ▼
         ┌────────┐      ┌─────────┐
         │ Watson │      │  Local  │
         │   AI   │      │  Model  │
         └────────┘      └─────────┘
```

### Key Components

#### 1. **Loaders** (`src/loaders/json_loader.py`)
- Parses JSON input documents
- Creates `Document` and `Paragraph` dataclasses
- Handles EN, DE, LV languages

#### 2. **Aligners** (`src/alignment/`)

**Simple Aligner** (`simple_aligner.py`):
- Rule-based index alignment
- Fast (~2 seconds)
- Assumes pre-aligned documents
- Now detects missing paragraphs (uses `max_len` instead of `min_len`)

**Semantic Aligner** (`paragraph_aligner.py`):
- Embedding-based alignment with **global Hungarian algorithm**
- Handles reordered/restructured content
- Detects DE/LV-only paragraphs
- Uses cosine similarity with tuned threshold (0.75)

#### 3. **Embeddings** (`embeddings.py`)
- Supports Watson AI and local models
- **Structured caching**: `(lang, index, text)` tuples prevent collisions
- Cache versioning with metadata validation
- Separate `.npz` for embeddings, `.json` for index mappings

#### 4. **Extractors** (`entity_extractor.py`)
- Regex-based entity extraction
- Supports:
  - Monetary values (EUR, USD, GBP, with scales)
  - Legal references (regulations, articles, cases)
  - Dates (multiple formats, multilingual)
- **Multilingual patterns**: English, German, Latvian

#### 5. **Validators** (`consistency_checker.py`)
- **Hungarian algorithm** for value-driven entity matching
- Compares DE-LV when EN missing
- Partial match support (EN-DE without LV)
- Generates `Difference` objects with severity levels

#### 6. **Reporters** (`report_generator.py`)
- JSON output (structured data)
- Excel output (human-readable, color-coded by severity)

---

## All Fixes Applied

### Security & Configuration (3)
1. ✅ **Hardcoded Credentials** - Removed from `config.py`, use environment variables
2. ✅ **Credential Validation** - Added `validate_watson_credentials()`
3. ✅ **Test Script Leak** - Fixed `test_watson_embeddings.py` to require valid credentials

### Alignment System (6)
4. ✅ **Wrong Model** - `embeddings.py` now uses `WATSON_EMBEDDING_MODEL` from config
5. ✅ **Index Mismatch** - `paragraph_aligner.py` tracks filtered→original indices with mappings
6. ✅ **SimpleAligner Truncation** - Uses `max_len`, detects missing paragraphs
7. ✅ **Greedy Alignment** - Replaced sequential matching with global Hungarian algorithm
8. ✅ **Unmatched Paragraphs** - Added post-pass to emit DE/LV-only content
9. ✅ **Empty Embeddings** - Added safety checks for empty/fully-excluded arrays

### Entity Matching (4)
10. ✅ **Positional Matching** - Implemented Hungarian algorithm for value-driven matching
11. ✅ **Partial Matches** - EN-DE pairs marked as matched even without LV
12. ✅ **Multilingual Regex** - Added German ("Artikel", "Absatz") and Latvian ("pants", "rindkopa")
13. ✅ **Cross-Language Comparison** - Added DE-LV comparison when EN missing

### Caching System (4)
14. ✅ **Cache Versioning** - Metadata includes model ID and embedding dimensions
15. ✅ **Cache Type Bug** - Index mappings stored in separate `.json` files
16. ✅ **Content-Based Keys** - Cache keys derived from `get_cache_key(documents)`
17. ✅ **Collision Prevention** - Ordered `(lang, index, text)` tuples in cache hash

### Thresholds & Tuning (2)
18. ✅ **Similarity Threshold** - Lowered from 0.85 to 0.75 (based on 0.83 benchmark)
19. ✅ **Matching Threshold** - Raised to 0.9 for currency/scale error detection

### User Interface (2)
20. ✅ **CLI Flags** - Added `--semantic`, `--watson`, `--local`
21. ✅ **Import Error** - Added `Tuple, Any` to `embeddings.py` typing imports

### Testing & Dependencies (2)
22. ✅ **Smoke Test** - Created `tests/test_imports.py` to catch import errors
23. ✅ **Dependencies** - Removed `python-docx`, `pandas`; added `scipy`

---

## Testing Guide

### Quick Tests

```bash
# Smoke test (all imports)
python3 tests/test_imports.py

# Full pipeline test
bash tests/test_pipeline.sh

# Simple alignment
python3 main.py

# Semantic alignment (local)
python3 main.py --semantic --local
```

### Component Tests

```bash
# Test JSON loader
python3 -c "
from src.loaders.json_loader import JSONLoader
from config import INPUT_FILES
docs = JSONLoader.load_all(INPUT_FILES)
print(f'Loaded: EN={len(docs[\"en\"])} DE={len(docs[\"de\"])} LV={len(docs[\"lv\"])} paragraphs')
"

# Test entity extractor
python3 -c "
from src.extractors.entity_extractor import EntityExtractor
extractor = EntityExtractor()
text = 'The facility is supported with EUR 520 million on 16/06/2023.'
entities = extractor.extract_all(text)
print(f'Monetary: {entities[\"monetary\"]}')
print(f'Dates: {entities[\"dates\"]}')
"

# Test embeddings (local)
python3 -c "
from src.alignment.embeddings import EmbeddingGenerator
gen = EmbeddingGenerator(use_watson=False)
emb = gen.generate(['test sentence'])
print(f'Embedding shape: {emb.shape}')
"

# Test cache key generation
python3 -c "
from src.alignment.embeddings import EmbeddingGenerator
from src.loaders.json_loader import JSONLoader
from config import INPUT_FILES
docs = JSONLoader.load_all(INPUT_FILES)
gen = EmbeddingGenerator(use_watson=False)
key = gen.get_cache_key(docs)
print(f'Cache key: {key}')
"
```

### Performance Testing

```bash
# Time simple alignment
time python3 main.py --format json

# Time semantic alignment (first run)
rm -rf .cache/*
time python3 main.py --semantic --local --format json

# Time semantic alignment (cached)
time python3 main.py --semantic --local --format json
```

### Output Validation

```bash
# Validate JSON
python3 -c "import json; json.load(open('output/differences.json')); print('✓ Valid JSON')"

# Count differences by type
python3 -c "
import json
data = json.load(open('output/differences.json'))
types = {}
for d in data.get('differences', []):
    error_type = d['error_type']
    types[error_type] = types.get(error_type, 0) + 1

for t, count in sorted(types.items(), key=lambda x: -x[1]):
    print(f'{t:25s} {count:4d}')
"

# Check Excel exists
ls -lh output/differences.xlsx
```

---

## Watson AI Setup

### Getting Credentials

1. **Sign up**: https://cloud.ibm.com/
2. **Create watsonx.ai instance**:
   - Go to Catalog → AI/Machine Learning → watsonx.ai
   - Select region (e.g., Dallas, Frankfurt)
   - Create service
3. **Get API Key**:
   - Go to Manage → Access (IAM)
   - API Keys → Create
4. **Get Project ID**:
   - Open watsonx.ai → Projects
   - Create new project or use existing
   - Copy Project ID from Settings

### Set Environment Variables

```bash
# Option 1: Export in terminal
export WATSON_API_KEY="your-api-key-here"
export WATSON_PROJECT_ID="your-project-id-here"
export WATSON_URL="https://us-south.ml.cloud.ibm.com"

# Option 2: Add to ~/.zshrc or ~/.bashrc
echo 'export WATSON_API_KEY="your-key"' >> ~/.zshrc
echo 'export WATSON_PROJECT_ID="your-id"' >> ~/.zshrc
source ~/.zshrc

# Option 3: Create .env file (use python-dotenv)
cat > .env <<EOF
WATSON_API_KEY=your-key
WATSON_PROJECT_ID=your-id
WATSON_URL=https://us-south.ml.cloud.ibm.com
EOF
```

### Validate Credentials

```bash
python3 -c "
from config import validate_watson_credentials
if validate_watson_credentials():
    print('✓ Credentials valid')
else:
    print('✗ Credentials missing or invalid')
"
```

### Test Watson Connection

```bash
# Quick test
python3 test_watson_embeddings.py

# Full run
python3 main.py --semantic --watson --format json
```

### Model Comparison

| Model | Dimensions | Cross-Lingual Similarity | Best For |
|-------|------------|-------------------------|----------|
| **granite-embedding-107m-multilingual** | 384 | **0.83** | Multilingual (EN/DE/LV) ✅ |
| slate-125m-english-rtrvr | 768 | 0.62 | English-only |
| slate-30m-english-rtrvr | 384 | 0.69 | Fast English |
| Local MiniLM-L6-v2 | 384 | 0.28 | Offline/development |

**Recommendation**: Use `granite-embedding-107m-multilingual` for production (already configured).

---

## Implementation Approach

### Detection Strategy

**Philosophy**: Prefer false positives over false negatives
- Better to flag 200 issues when there are 100 real errors
- Human reviewers filter false positives more easily than finding missed errors

### Error Types & Severity

| Error Type | Description | Severity |
|------------|-------------|----------|
| MISSING_VALUE | Entity in some languages but not others | CRITICAL |
| MONETARY_VALUE | Amount differences across languages | CRITICAL |
| CURRENCY_MISMATCH | Different currencies (EUR vs USD) | CRITICAL |
| SCALE_ERROR | Million vs billion mismatch | CRITICAL |
| DATE_VALUE | Date discrepancies | CRITICAL |
| LEGAL_REFERENCE | Regulation/article mismatches | CRITICAL |
| MISSING_PARAGRAPH | Paragraph in some languages only | CRITICAL |

All errors are marked CRITICAL to ensure review.

### Alignment Methods

#### Simple Alignment (Rule-Based)
- **When to use**: Documents with same paragraph order
- **Pros**: Fast (~2s), deterministic
- **Cons**: Misses reordered content
- **Algorithm**: Direct index mapping with missing paragraph detection

#### Semantic Alignment (Embedding-Based)
- **When to use**: Documents may be reordered/restructured
- **Pros**: Handles restructuring, finds best matches
- **Cons**: Slower (~15s first run), needs tuning
- **Algorithm**: Global Hungarian assignment on cosine similarity matrix

### Entity Matching

**Old approach** (positional):
```python
# Assumes same order - WRONG
for i in range(max_count):
    en_val = en_entities[i]
    de_val = de_entities[i]  # May not be the same entity!
```

**New approach** (value-driven with Hungarian):
```python
# Build cost matrix based on entity similarity
cost_matrix = compute_entity_distance(en_entities, de_entities)
# Find optimal global assignment
en_indices, de_indices = linear_sum_assignment(cost_matrix)
# Match only if similarity meets threshold
matches = [(i, j) for i, j in zip(en_indices, de_indices) if cost_matrix[i,j] < 0.9]
```

### Partial Language Comparison

When one language is missing (e.g., EN missing but DE/LV present):
1. Report missing paragraph
2. **Also compare available languages** (DE vs LV)
3. Catch inconsistencies even when reference language is absent

---

## Optimization Work

### Performance Optimizations

1. **Embedding Cache**:
   - Saves ~12s per run after first execution
   - Content-based keys prevent stale cache
   - Metadata validation ensures model consistency

2. **Global Hungarian Assignment**:
   - Eliminates greedy match-stealing
   - Computes full cost matrix upfront
   - Finds optimal alignment across all paragraphs

3. **Structured Index Mappings**:
   - Tracks filtered→original paragraph indices
   - Prevents off-by-one errors with blank paragraphs
   - Stored separately from embeddings

### Quality Optimizations

1. **Threshold Tuning**:
   - Lowered from 0.85 to 0.75 based on empirical testing
   - Watson Granite averages 0.83, threshold must be below

2. **Value-Driven Matching**:
   - Entities matched by value similarity, not position
   - Handles reordered translations correctly

3. **Partial Match Support**:
   - EN-DE pairs processed even without LV
   - Avoids duplicate "missing" errors

4. **Cross-Language Validation**:
   - Compares DE-LV when EN absent
   - Prevents blind spots in validation

### Code Quality

1. **Type Safety**: Full type hints with `typing` module
2. **Error Handling**: Graceful degradation for empty arrays
3. **Modularity**: Clear separation of concerns
4. **Testing**: Smoke tests + component tests + pipeline test
5. **Documentation**: Inline comments for complex logic

---

## Configuration Reference

### `config.py` Settings

```python
# Watson AI Configuration
WATSON_EMBEDDING_MODEL = "ibm/granite-embedding-107m-multilingual"  # Best multilingual
WATSON_URL = "https://us-south.ml.cloud.ibm.com"
WATSON_API_KEY = os.getenv("WATSON_API_KEY", "")
WATSON_PROJECT_ID = os.getenv("WATSON_PROJECT_ID", "")

# Local Fallback
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Thresholds (tuned based on testing)
SIMILARITY_THRESHOLD = 0.75  # Paragraph alignment (Granite averages 0.83)
NUMERICAL_TOLERANCE = 0.01   # Monetary value comparison

# Error Severity Levels
ERROR_TYPES = {
    "MISSING_VALUE": "CRITICAL",
    "MONETARY_VALUE": "CRITICAL",
    "CURRENCY_MISMATCH": "CRITICAL",
    "SCALE_ERROR": "CRITICAL",
    "DATE_VALUE": "CRITICAL",
    "LEGAL_REFERENCE": "CRITICAL",
    "ARTICLE_REFERENCE": "CRITICAL",
}
```

### Directory Structure

```
.cache/                              # Embedding cache (auto-created)
  ├── <model_id>_<hash>_embeddings.npz  # Cached embeddings
  └── <model_id>_<hash>_mappings.json   # Index mappings

output/                              # Generated reports (auto-created)
  ├── differences.json               # Structured output
  └── differences.xlsx               # Human-readable report

data/                                # Input documents
  ├── test_sample_en_parsed.json
  ├── test_sample_de_parsed.json
  └── test_sample_lv_parsed.json
```

---

## Known Limitations & Future Work

### Current Limitations

1. **Translation Variations**: Legitimate rephrasing may be flagged as errors
2. **Regex-Based Extraction**: Complex/unusual entity formats may be missed
3. **No Context Awareness**: Can't distinguish intentional vs erroneous differences
4. **Threshold Sensitivity**: May need tuning for different document types

### Planned Enhancements

- [ ] LLM-based arbitration for borderline cases
- [ ] Custom regex patterns per document type
- [ ] Confidence scoring for each difference
- [ ] Interactive review interface
- [ ] Multi-document batch processing
- [ ] Historical comparison (track changes over versions)

---

## Support & Maintenance

### Monitoring in Production

```bash
# Check execution time
time python3 main.py --semantic --watson

# Monitor cache size
du -sh .cache/

# Validate output
python3 -c "import json; data=json.load(open('output/differences.json')); print(f'Differences: {len(data[\"differences\"])}')"

# Check error distribution
python3 -c "
import json
from collections import Counter
data = json.load(open('output/differences.json'))
types = Counter(d['error_type'] for d in data['differences'])
print(types)
"
```

### Troubleshooting Checklist

- [ ] All modules import successfully (`python3 tests/test_imports.py`)
- [ ] Watson credentials valid (if using Watson)
- [ ] Input files exist in `data/` directory
- [ ] Python 3.8+ installed
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Sufficient disk space for cache
- [ ] Output directory writable

---

**Document Version**: 1.0
**Last Updated**: 2025-10-29
**Status**: ✅ Complete & Production Ready
