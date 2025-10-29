# Document Consistency Checker

**IBM Hackathon Project** - Multilingual Legal Document Validation System

## Overview

This tool automatically detects inconsistencies across multilingual legal documents (English, German, Latvian). It identifies critical errors in:
- ✅ **Monetary values** (amounts, currencies, scales)
- ✅ **Legal references** (regulations, articles, cases)
- ✅ **Dates** (value mismatches, missing specific dates)
- ✅ **Missing values** (vague vs. specific information)

**Strategy**: Prefer false positives over false negatives - better to flag 200 when there are 100 errors.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the checker
python3 main.py

# View results
open output/differences.xlsx
```

## Results

Found **50 differences** in test documents:
- 36 missing values
- 12 monetary value discrepancies
- 1 currency mismatch
- 1 scale error

See [output/differences.xlsx](output/differences.xlsx) for full report.

## Documentation

- [ANALYSIS.md](ANALYSIS.md) - Test data analysis
- [WATSON_AI_GUIDE.md](WATSON_AI_GUIDE.md) - Watson AI integration guide  
- [UPDATED_APPROACH.md](UPDATED_APPROACH.md) - Implementation approach

## Team

Karla Lucic & Claude AI
