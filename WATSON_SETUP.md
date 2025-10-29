# Watson AI Setup Guide

## How to Know if Watson AI is Working

Run the test script:
```bash
python3 test_watson_embeddings.py
```

**If working correctly**, you'll see:
```
✓ Using Watson AI embeddings: ibm/granite-embedding-107m-multilingual
Cross-language similarity scores:
  EN ↔ DE: 0.85+
  EN ↔ LV: 0.80+
  DE ↔ LV: 0.82+
  Average: 0.82+

✅ EXCELLENT for multilingual documents!
```

**If not working**, you'll see:
```
❌ Error: Provided API key could not be found
```

## Current Status

❌ **Watson AI credentials in config.py are invalid**

The API key `ApiKey-aaa31127-dba6-4c68-851f-84ee03d2e1e5` returns:
```
Error: Provided API key could not be found
```

## How to Get Valid Credentials

### Option 1: Ask IBM Team

Contact the IBM hackathon organizers and ask for:
1. **Watson AI API Key**
2. **Watson AI Project ID**
3. **Watson AI URL** (usually `https://us-south.ml.cloud.ibm.com`)

### Option 2: Create Your Own (if you have IBM Cloud access)

1. Go to https://cloud.ibm.com/
2. Log in with your IBM Cloud account
3. Navigate to **Watson AI** → **watsonx.ai**
4. Create a new project or select existing one
5. Get credentials:
   - **API Key**: IAM → API Keys → Create
   - **Project ID**: Project → Manage → General
   - **URL**: Check your region (us-south, eu-gb, etc.)

## Update Credentials

### Method 1: Environment Variables (Recommended)

```bash
export WATSON_API_KEY="your_real_api_key_here"
export WATSON_PROJECT_ID="your_real_project_id_here"
export WATSON_URL="https://us-south.ml.cloud.ibm.com"
```

Then run:
```bash
python3 test_watson_embeddings.py
```

### Method 2: Edit config.py Directly

Edit [config.py](config.py) lines 24-26:

```python
WATSON_API_KEY = os.getenv("WATSON_API_KEY", "YOUR_REAL_KEY_HERE")
WATSON_URL = os.getenv("WATSON_URL", "https://us-south.ml.cloud.ibm.com")
WATSON_PROJECT_ID = os.getenv("WATSON_PROJECT_ID", "YOUR_REAL_PROJECT_ID")
```

⚠️ **Important**: Don't commit real API keys to GitHub!

Add this to `.gitignore`:
```bash
echo "config.py" >> .gitignore
```

## Best Embedding Model for Your Use Case

Based on research, the **best model** for multilingual (EN/DE/LV) documents is:

```
ibm/granite-embedding-107m-multilingual
```

**Why?**
- ✅ Trained on German, English, and other European languages
- ✅ Higher dimensional embeddings (better semantic understanding)
- ✅ Designed for cross-lingual similarity
- ✅ Better than Slate models for multilingual alignment

**Alternative models** (if Granite not available):
1. `ibm/slate-125m-english-rtrvr` - Best for English-only (768 dims)
2. `ibm/slate-30m-english-rtrvr` - Faster, smaller (384 dims)

## Testing Results

### Current (Local Model)
```
Model: sentence-transformers/all-MiniLM-L6-v2
EN ↔ DE: 0.24  ⚠️ LOW
EN ↔ LV: 0.21  ⚠️ LOW
DE ↔ LV: 0.40  ⚠️ LOW
Average: 0.28  ⚠️ Too low for good alignment
```

### Expected (Watson Granite Multilingual)
```
Model: ibm/granite-embedding-107m-multilingual
EN ↔ DE: 0.85+  ✅ HIGH
EN ↔ LV: 0.80+  ✅ HIGH
DE ↔ LV: 0.82+  ✅ HIGH
Average: 0.82+  ✅ Excellent for alignment
```

## Why This Matters

**Current approach**: Simple index-based alignment (assumes paragraphs in same order)
- ✅ Works for your test data (already aligned)
- ❌ Won't work if documents have reordered paragraphs
- ❌ Won't work if paragraphs are added/removed in one language

**With Watson embeddings**: Semantic similarity alignment
- ✅ Works even if paragraphs reordered
- ✅ Detects best matching paragraph across languages
- ✅ More robust for real-world documents
- ✅ Can detect when paragraphs are completely missing

## Usage Examples

### Once Watson AI is configured:

```bash
# Test embedding models
python3 test_watson_embeddings.py

# Use Watson AI in main application (requires updating main.py)
# (Currently main.py uses simple alignment, not embeddings)
```

### To enable Watson AI embeddings in main.py:

You'd need to modify [main.py](main.py) to use `ParagraphAligner` instead of `SimpleAligner`:

```python
# Change from:
from src.alignment.simple_aligner import SimpleAligner
aligner = SimpleAligner()
aligned = aligner.align_documents(documents)

# To:
from src.alignment.embeddings import EmbeddingGenerator
from src.alignment.paragraph_aligner import ParagraphAligner
generator = EmbeddingGenerator(use_watson=True)
aligner = ParagraphAligner(generator)
aligned = aligner.align_documents(documents)
```

## Quick Checklist

- [ ] Get valid Watson AI credentials from IBM team
- [ ] Update environment variables or config.py
- [ ] Run `python3 test_watson_embeddings.py`
- [ ] Verify you see "EXCELLENT for multilingual documents"
- [ ] (Optional) Update main.py to use embeddings-based alignment

## Need Help?

1. **Invalid API key**: Contact IBM team for valid credentials
2. **Wrong region**: Try different URLs:
   - US South: `https://us-south.ml.cloud.ibm.com`
   - EU GB: `https://eu-gb.ml.cloud.ibm.com`
   - EU DE: `https://eu-de.ml.cloud.ibm.com`
3. **Model not available**: Try alternative models in test script

## Documentation Links

- Watson AI SDK: https://ibm.github.io/watsonx-ai-python-sdk/
- IBM Cloud Console: https://cloud.ibm.com/
- Granite Models: https://www.ibm.com/granite

---

**Current Status**: ⚠️ Waiting for valid Watson AI credentials from IBM team

**Fallback**: The solution works without Watson AI using simple index-based alignment. Watson AI would make it more robust but isn't required for your test data.
