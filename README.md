# Document Consistency Checker

**IBM Hackathon Project** - Multilingual Legal Document Validation System

Automatically detects inconsistencies across English, German, and Latvian legal documents.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
bash tests/test_pipeline.sh

# Run the checker (simple mode - fastest)
python3 main.py

# Run with semantic alignment (better quality)
python3 main.py --semantic --local

# View results
open output/differences.xlsx
```

---

## Features

- **Monetary Values**: Detects amount, currency, and scale mismatches
- **Legal References**: Validates regulations, articles, and case numbers
- **Dates**: Finds date discrepancies and vague vs specific values
- **Missing Content**: Identifies paragraphs present in some languages but not others
- **Two Alignment Modes**: Rule-based (fast) and semantic (accurate)
- **Watson AI Support**: Uses IBM Granite multilingual embeddings

---

## Results

**Test Dataset**: 70 paragraphs × 3 languages

**Differences Found**: 173

**Error Types**:
- Missing values (entity in one language but not others)
- Monetary value discrepancies
- Currency/scale mismatches
- Date inconsistencies
- Legal reference differences
- Missing paragraphs

See `output/differences.xlsx` for detailed report.

---

## Usage

### Command Line Options

```bash
python3 main.py [OPTIONS]

Options:
  --format {json,excel,both}  Output format (default: both)
  --semantic                  Use semantic alignment (vs simple rule-based)
  --watson                    Use Watson AI embeddings (requires credentials)
  --local                     Use local embeddings model
```

### Examples

```bash
# Simple alignment (fastest, ~2 seconds)
python3 main.py

# Semantic with local model (~15 seconds first run, ~3s cached)
python3 main.py --semantic --local

# Semantic with Watson AI (best quality, ~20 seconds)
export WATSON_API_KEY="your-key"
export WATSON_PROJECT_ID="your-project-id"
python3 main.py --semantic --watson
```

---

## Project Structure

```
team-ibm-project/
├── main.py                      # CLI entry point
├── config.py                    # Configuration
├── requirements.txt             # Dependencies
├── data/                        # Input JSON files
├── src/
│   ├── loaders/                 # Document loading
│   ├── alignment/               # Paragraph alignment (simple + semantic)
│   ├── extractors/              # Entity extraction (regex-based)
│   ├── validators/              # Consistency checking
│   └── output/                  # Report generation
├── tests/                       # Test suite
├── output/                      # Generated reports
└── .cache/                      # Embedding cache
```

---

## Configuration

### Watson AI Setup (Optional)

For best quality results, configure Watson AI credentials:

```bash
# Set environment variables
export WATSON_API_KEY="your-api-key"
export WATSON_PROJECT_ID="your-project-id"
export WATSON_URL="https://us-south.ml.cloud.ibm.com"

# Test credentials
python3 -c "from config import validate_watson_credentials; print('Valid' if validate_watson_credentials() else 'Invalid')"

# Run with Watson
python3 main.py --semantic --watson
```

Get credentials from: https://cloud.ibm.com/

### Tuning Thresholds

Edit `config.py`:

```python
SIMILARITY_THRESHOLD = 0.75  # For paragraph alignment (0-1)
NUMERICAL_TOLERANCE = 0.01   # For monetary values
```

---

## Testing

```bash
# Run comprehensive test suite
bash tests/test_pipeline.sh

# Run individual tests
python3 tests/test_imports.py                    # Module imports
python3 src/loaders/json_loader.py               # JSON loader
python3 src/extractors/entity_extractor.py       # Entity extraction
python3 src/alignment/simple_aligner.py          # Simple alignment
python3 src/validators/consistency_checker.py    # Consistency checking

# Clear cache
rm -rf .cache/*
```

---

## Performance

| Mode | First Run | Cached Run | Accuracy |
|------|-----------|------------|----------|
| Simple (rule-based) | ~2s | ~2s | Good |
| Semantic (local) | ~15s | ~3s | Better |
| Semantic (Watson) | ~20s | ~5s | Best (0.83) |

**Watson Granite Model**: 0.83 cross-lingual similarity (vs 0.28 local model)

---

## Troubleshooting

### Import Errors
```bash
python3 tests/test_imports.py
```

### Watson Credentials
```bash
python3 -c "from config import validate_watson_credentials; validate_watson_credentials()"
```

### Cache Issues
```bash
rm -rf .cache/*
```

### Output Validation
```bash
python3 -c "import json; data=json.load(open('output/differences.json')); print(f'Found {len(data[\"differences\"])} differences')"
```

---

## Technical Details

For architecture, implementation details, and optimization work, see:
- **`TECHNICAL_DETAILS.md`** - Complete technical documentation

---

## Team

- Karla Lucic
- Ante Kuvacic
- Eren Can
- Vicente Caldeira

**Status**: Production Ready (23/23 critical issues resolved)

**License**: MIT
