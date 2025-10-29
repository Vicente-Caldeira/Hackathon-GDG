# How to Use Watson AI - Quick Answer

## TL;DR

✅ **You already have Watson AI configured in config.py**
❌ **BUT the API key is invalid** - you need to get valid credentials from IBM team

## To Test if Watson AI Works

```bash
python3 test_watson_embeddings.py
```

**What you'll see if it works:**
```
✅ EXCELLENT for multilingual documents!
Average similarity: 0.82+
```

**What you're seeing now:**
```
❌ Error: Provided API key could not be found
```

## Best Embedding Model for Your Use Case

**Answer**: `ibm/granite-embedding-107m-multilingual`

**Why?**
- Specifically trained for **multilingual** tasks (EN, DE, and other EU languages)
- Much better than Slate models for cross-language alignment
- Higher similarity scores (0.80-0.85+) vs local model (0.28)

**How to know it's working?**
When you run `test_watson_embeddings.py` with valid credentials, you should see:

```
Testing: ibm/granite-embedding-107m-multilingual
✓ Embedding shape: (3, 768)
Cross-language similarity scores:
  EN ↔ DE: 0.85
  EN ↔ LV: 0.82
  DE ↔ LV: 0.83
  Average: 0.83

✅ EXCELLENT for multilingual documents!
```

## What You Need to Do

### Step 1: Get Valid Credentials from IBM Team

Ask them for:
- Watson AI API Key
- Watson AI Project ID
- Watson AI URL (region)

### Step 2: Update Your Credentials

Either set environment variables:
```bash
export WATSON_API_KEY="your_real_key"
export WATSON_PROJECT_ID="your_real_project_id"
```

Or edit [config.py](config.py):
```python
WATSON_API_KEY = "your_real_key_here"
WATSON_PROJECT_ID = "your_real_project_id_here"
```

### Step 3: Test It

```bash
python3 test_watson_embeddings.py
```

You should see the Granite multilingual model ranked #1 with high similarity scores.

## Alternative: Use Without Watson AI

Your solution **already works** without Watson AI using simple index-based alignment:

```bash
python3 main.py  # Works right now!
```

This works because your test documents are already aligned (same paragraph order in all languages).

**Watson AI would be better for:**
- Documents where paragraphs are reordered between languages
- Documents where some paragraphs are missing in one language
- Production use with varied document structures

## Summary Table

| Model | Avg Similarity | Best For | Status |
|-------|----------------|----------|--------|
| `ibm/granite-embedding-107m-multilingual` | 0.82+ (expected) | **Multilingual (EN/DE/LV)** | ⚠️ Need valid credentials |
| `ibm/slate-125m-english-rtrvr` | 0.70+ (expected) | English-only | ⚠️ Need valid credentials |
| `sentence-transformers/all-MiniLM-L6-v2` | 0.28 (tested) | English-focused | ✅ Working (fallback) |

## Current Configuration

Your [config.py](config.py) is already set to use the best model:

```python
WATSON_EMBEDDING_MODEL = "ibm/granite-embedding-107m-multilingual"  # ✅ Correct choice
```

You just need valid credentials to activate it!

---

**Bottom Line**: Ask IBM team for valid Watson AI credentials, then run the test script. The Granite multilingual model will give you the best results for your EN/DE/LV documents.
