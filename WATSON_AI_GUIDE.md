# Watson AI Integration Guide for Document Consistency Checker

## Overview

Based on IBM team feedback, we have **2 implementation paths**:
1. **Prompt-based approach**: Deploy prompts via Watson AI
2. **Hybrid approach**: Use Watson AI for embeddings + local processing

## What is watsonx.ai?

**watsonx.ai** is IBM's enterprise AI platform that provides:
- **Foundation Models**: Pre-trained LLMs (Llama, Granite, etc.)
- **Prompt Lab**: Create, test, and deploy prompts
- **Embeddings**: Generate vector representations for semantic search
- **Model Deployment**: Deploy custom models and prompts via API
- **Storage**: Store embeddings, prompts, and model assets

## When to Use Watson AI for This Project

### ✅ **Use Watson AI For:**

1. **Embeddings Generation** (Primary Use Case)
   - Generate embeddings for each paragraph across all 3 languages
   - Enable semantic similarity matching for paragraph alignment
   - Store embeddings in Watson AI for reuse
   - **Why**: Better than simple text matching when paragraph order differs

2. **Prompt Deployment** (LLM-based Detection)
   - Deploy prompts that identify inconsistencies
   - Use LLMs to understand context and detect subtle errors
   - **Why**: Can catch semantic inconsistencies, not just syntactic ones

3. **Batch Processing**
   - Process multiple documents at scale
   - **Why**: Enterprise-grade infrastructure

### ❌ **Don't Use Watson AI For:**

1. **Simple Pattern Matching**
   - Regex-based detection (dates, numbers, references)
   - **Why**: Overkill, slower, unnecessary API costs

2. **Exact String Comparison**
   - Comparing identical values across languages
   - **Why**: Can be done locally much faster

## Implementation Strategy

### **Hybrid Approach (Recommended)**

```
┌─────────────────────────────────────────────────────────┐
│                    INPUT: JSON FILES                     │
│           (test_sample_en/de/lv_parsed.json)            │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│              STEP 1: LOCAL PREPROCESSING                 │
│  • Parse JSON structure                                  │
│  • Extract entities (dates, numbers, references)         │
│  • Normalize formatting                                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│         STEP 2: WATSON AI - EMBEDDING GENERATION         │
│  • Send paragraphs to watsonx.ai Embeddings API          │
│  • Generate vectors for each paragraph (all languages)   │
│  • Store embeddings in Watson AI storage                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│            STEP 3: LOCAL - PARAGRAPH ALIGNMENT           │
│  • Calculate cosine similarity between embeddings        │
│  • Align EN ↔ DE ↔ LV paragraphs                        │
│  • Handle missing/extra paragraphs                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│          STEP 4: LOCAL - RULE-BASED VALIDATION           │
│  • Compare dates (format-agnostic)                       │
│  • Validate monetary values (CRITICAL)                   │
│  • Check legal references (CRITICAL)                     │
│  • Detect missing values (CRITICAL)                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│     STEP 5: WATSON AI - LLM-BASED VALIDATION (Optional)  │
│  • Send ambiguous cases to deployed prompt               │
│  • Ask LLM: "Are these semantically equivalent?"         │
│  • Get confidence scores                                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                OUTPUT: DIFFERENCES LIST                  │
│           (JSON + Excel with all differences)            │
│  • Prefer false positives over false negatives           │
│  • Flag everything suspicious                            │
└─────────────────────────────────────────────────────────┘
```

## Watson AI Setup

### 1. **Prerequisites**

```bash
pip install ibm-watsonx-ai
```

### 2. **Authentication**

```python
from ibm_watsonx_ai import Credentials

credentials = Credentials(
    url="https://us-south.ml.cloud.ibm.com",  # or your region
    api_key="YOUR_IBM_CLOUD_API_KEY"
)
```

### 3. **Project/Space Setup**

You need either a **project_id** or **space_id** (deployment space):
- **Project**: Development environment
- **Space**: Production deployment environment

Find these in watsonx.ai under: **Manage → General**

## Code Examples

### **Example 1: Generate Embeddings**

```python
from ibm_watsonx_ai.foundation_models import Embeddings

# Initialize embeddings model
embeddings = Embeddings(
    model_id="ibm/slate-125m-english-rtrvr",  # or other embedding model
    credentials=credentials,
    project_id="YOUR_PROJECT_ID"
)

# Generate embeddings for paragraphs
paragraphs_en = [
    "REGULATION (EU) 2025/… OF THE EUROPEAN PARLIAMENT",
    "of 18 March 2025",
    "establishing the Reform and Growth Facility"
]

# Get embeddings
vectors = embeddings.embed_documents(paragraphs_en)

# Store for later use
import json
with open('embeddings_en.json', 'w') as f:
    json.dump({
        'paragraphs': paragraphs_en,
        'embeddings': [vec.tolist() for vec in vectors]
    }, f)
```

### **Example 2: Paragraph Alignment with Embeddings**

```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Load embeddings for all languages
en_vectors = np.array(embeddings_en)
de_vectors = np.array(embeddings_de)

# Calculate similarity matrix
similarity_matrix = cosine_similarity(en_vectors, de_vectors)

# Find best matches
for i, en_para in enumerate(paragraphs_en):
    best_match_idx = np.argmax(similarity_matrix[i])
    similarity_score = similarity_matrix[i][best_match_idx]

    if similarity_score > 0.85:  # High confidence match
        print(f"EN para {i} ↔ DE para {best_match_idx} (score: {similarity_score:.2f})")
    else:
        print(f"⚠️ EN para {i} has no good match! (best score: {similarity_score:.2f})")
```

### **Example 3: Deploy Prompt for Error Detection**

```python
from ibm_watsonx_ai.foundation_models import ModelInference

# Initialize model
model = ModelInference(
    model_id="meta-llama/llama-3-70b-instruct",
    credentials=credentials,
    project_id="YOUR_PROJECT_ID"
)

# Create prompt for detecting inconsistencies
prompt_template = """You are a legal document QA assistant. Compare these three translations:

EN: {en_text}
DE: {de_text}
LV: {lv_text}

Focus on:
1. Monetary values (must be EXACTLY the same)
2. Legal references (regulation numbers, articles)
3. Dates (format doesn't matter, but DATE must be same)
4. Missing values (if one version has specific info, others should too)

List ALL differences you find. Be thorough - false positives are better than missing errors.
"""

# Use it
result = model.generate_text(
    prompt=prompt_template.format(
        en_text="EUR 1,500 million",
        de_text="1,5 Mrd. USD",
        lv_text="1,500 miljonu EUR"
    )
)

print(result)  # Will flag the USD vs EUR discrepancy
```

### **Example 4: Store Embeddings in Watson AI**

```python
from ibm_watsonx_ai import APIClient

client = APIClient(credentials)
client.set.default_project("YOUR_PROJECT_ID")

# Store embeddings as an asset
metadata = {
    "name": "document_embeddings_en",
    "description": "Paragraph embeddings for English test sample",
    "asset_type": "data_asset"
}

# Upload to Watson AI storage
asset_details = client.data_assets.store(
    meta_props=metadata,
    data=embeddings_data  # Your embeddings as bytes
)

print(f"Stored with asset ID: {asset_details['metadata']['asset_id']}")
```

## Critical Detection Rules (from IBM Feedback)

### ✅ **Must Detect (High Priority)**

1. **Monetary Values**
   - Different amounts: `EUR 135 million` vs `136 Mio. EUR` ❌
   - Different currencies: `EUR 1500 million` vs `1,5 Mrd USD` ❌
   - Scale errors: `million` vs `billion` (`miljonu` vs `miljardi`) ❌

2. **Legal References**
   - Regulation numbers: `(EU) 2022/947` vs `(EU) 2021/947` ❌
   - Article numbers: `Art 19(2)` vs `Art 19(3)` ❌
   - Wrong prefix: `(EU)` vs `(ER)` vs `(ES)` ❌

3. **Missing Values**
   - EN: "on 18 March 2025"
   - LV: "in 2 weeks" ← **Missing specific date** ❌

### ⚠️ **Ignore (Acceptable Variations)**

1. **Date Formats**
   - `16/06/2023` vs `2023-06-16` vs `16.06.2023` ✅ (same date)

2. **Number Formatting**
   - `1,500` vs `1.500` vs `1 500` ✅ (just formatting)

3. **Abbreviations**
   - `million` vs `Mio.` vs `miljonu` ✅ (translation variation)

## Detection Strategy: Prefer False Positives

> "False negatives are worse. Now: 100 errors, tool spots 200"

**Approach:**
- Flag **everything** that looks remotely suspicious
- Let human reviewers filter false positives
- Better to flag `0.32` vs `0.3` even if it might be rounding
- **Never miss** critical errors (amounts, references, dates)

```python
# Example: Aggressive detection
def compare_amounts(en_val, de_val, lv_val):
    """Compare monetary values - very strict"""

    # Normalize to same format
    en_normalized = normalize_amount(en_val)
    de_normalized = normalize_amount(de_val)
    lv_normalized = normalize_amount(lv_val)

    # Even tiny differences get flagged
    tolerance = 0.01  # 1 cent tolerance

    if not (
        abs(en_normalized - de_normalized) < tolerance and
        abs(en_normalized - lv_normalized) < tolerance
    ):
        return {
            "error_type": "MONETARY_MISMATCH",
            "severity": "CRITICAL",
            "en": en_val,
            "de": de_val,
            "lv": lv_val,
            "confidence": "HIGH"
        }
```

## Output Format

Based on feedback: **"List of differences"**

### JSON Output
```json
{
  "document_set": "test_sample",
  "total_differences": 41,
  "differences": [
    {
      "paragraph": "(12)",
      "type": "DATE_MISMATCH",
      "severity": "MEDIUM",
      "en": "16/06/2023",
      "de": "15/06/2023",
      "lv": "16/06/2023",
      "description": "Date differs in German version"
    },
    {
      "paragraph": "(29)",
      "type": "MONETARY_VALUE",
      "severity": "CRITICAL",
      "en": "EUR 1500 million",
      "de": "1,5 Mrd USD",
      "lv": "1500 miljonu EUR",
      "description": "Currency mismatch: USD vs EUR"
    }
  ]
}
```

### Excel Output (Same as errors_test_file.xlsx)
| Paragraph | EN | DE | LV | Error Type | Severity |
|-----------|----|----|----|-----------|---------|
| (12) | 16/06/2023 | 15/06/2023 | 16/06/2023 | DATE | MEDIUM |
| (29) | EUR 1500 million | 1,5 Mrd USD | 1500 miljonu EUR | MONETARY | CRITICAL |

## Resources

### Official Documentation
- **Watson AI Python SDK**: https://ibm.github.io/watsonx-ai-python-sdk/
- **API Docs**: https://cloud.ibm.com/apidocs/watsonx-ai
- **EU Style Guide**: https://style-guide.europa.eu/en/ (for validation rules)

### Available Embedding Models
- `ibm/slate-125m-english-rtrvr` - English retrieval
- `ibm/slate-30m-english-rtrvr` - Faster, smaller
- `sentence-transformers/all-MiniLM-L6-v2` - Multilingual

### Available LLMs for Prompts
- `meta-llama/llama-3-70b-instruct` - Best reasoning
- `ibm/granite-13b-chat-v2` - IBM's model
- `mistralai/mixtral-8x7b-instruct-v01` - Good for multilingual

## Cost Considerations

**Embeddings**:
- ~65 paragraphs × 3 languages = 195 embedding calls
- Cost: Minimal (embeddings are cheap)

**LLM Prompts**:
- Use sparingly for ambiguous cases only
- Cost: Higher, but controlled if used selectively

**Storage**:
- Store embeddings once, reuse many times
- Practically free for this scale

## Next Steps

1. ✅ Set up IBM Cloud account + watsonx.ai access
2. ✅ Get API key and project ID
3. ✅ Install `ibm-watsonx-ai` Python SDK
4. ✅ Test embedding generation on sample data
5. ✅ Implement paragraph alignment algorithm
6. ✅ Build rule-based validators (references, amounts)
7. ✅ Deploy prompt for edge cases (optional)
8. ✅ Generate difference reports (JSON + Excel)

## Questions to Ask IBM Team

1. **Do you have a watsonx.ai project already set up?**
   - If yes: Get project_id
   - If no: Need to create one

2. **Do you have API keys/credentials?**
   - Need IBM Cloud API key

3. **Which embedding model should we use?**
   - Recommendation: `ibm/slate-125m-english-rtrvr` (supports multilingual)

4. **Should we deploy a prompt, or just use embeddings?**
   - Embeddings = faster, cheaper, sufficient for most cases
   - Prompts = better for semantic understanding, more expensive

5. **Where should we store embeddings?**
   - Watson AI storage (recommended for collaboration)
   - Local files (faster for development)

6. **What's the budget for API calls?**
   - Will determine how much we use LLMs vs rule-based logic
