# Critical Fixes Applied

## ✅ COMPLETED

### 1. Security: Removed Hardcoded Credentials
**Issue**: config.py exposed live IBM Cloud API credentials
**Fix**:
- Removed all hardcoded API keys
- Added credential validation helpers
- Added security warnings in comments
- Credentials now MUST be set via environment variables

**Files Modified**: `config.py` lines 23-30, 62-79

### 2. Embeddings Configuration
**Issue**: embeddings.py ignored WATSON_EMBEDDING_MODEL setting
**Fix**:
- Now uses `WATSON_EMBEDDING_MODEL` from config (granite-embedding-107m-multilingual)
- Added credential validation before Watson initialization
- Logs which model is being used
- Gracefully falls back to local model if Watson unavailable

**Files Modified**: `src/alignment/embeddings.py` lines 9-13, 38-65

## 🚧 REMAINING CRITICAL FIXES NEEDED

### 3. Paragraph Aligner Index Mismatch (CRITICAL)
**Issue**: Filters blank paragraphs before embedding but indexes into original list
**Location**: `src/alignment/paragraph_aligner.py` lines 88-154
**Impact**: Index errors or wrong matches when documents have blank paragraphs

**Required Fix**:
```python
# In _get_embeddings(), track mapping between filtered and original indices
def _get_embeddings(self, documents, use_cache):
    embeddings = {}
    index_mappings = {}  # NEW: track filtered -> original mapping

    for lang, doc in documents.items():
        # Filter and track indices
        non_empty_paras = []
        mapping = []
        for i, p in enumerate(doc.paragraphs):
            if p.text.strip():
                non_empty_paras.append(p.text)
                mapping.append(i)  # Track original index

        embeddings[lang] = self.embedding_generator.generate(non_empty_paras)
        index_mappings[lang] = mapping

    return embeddings, index_mappings

# Update _align_with_reference() to use mappings
```

### 4. SimpleAligner Missing Paragraph Detection
**Issue**: Truncates to shortest document, doesn't flag missing paragraphs
**Location**: `src/alignment/simple_aligner.py` lines 52-63
**Impact**: Structural differences never surface (contradicts IBM requirements)

**Required Fix**:
```python
def align_documents(self, documents):
    max_len = max(len(doc) for doc in documents.values())

    aligned = []
    for i in range(max_len):
        para_en = documents['en'].paragraphs[i] if i < len(documents['en']) else None
        para_de = documents['de'].paragraphs[i] if i < len(documents['de']) else None
        para_lv = documents['lv'].paragraphs[i] if i < len(documents['lv']) else None

        aligned.append(AlignedParagraphs(en=para_en, de=para_de, lv=para_lv))

    return aligned
```

### 5. Versioned Embedding Cache
**Issue**: Cache filename doesn't encode model/documents, reuses stale vectors
**Location**: `src/alignment/embeddings.py` lines 95-108

**Required Fix**:
```python
import hashlib

def _get_cache_key(self, documents, model_id):
    """Generate cache key from documents and model."""
    # Hash document contents
    content_hash = hashlib.md5()
    for lang in sorted(documents.keys()):
        for para in documents[lang].paragraphs:
            content_hash.update(para.text.encode('utf-8'))

    # Include model in key
    return f"{model_id.replace('/', '_')}_{content_hash.hexdigest()[:8]}"
```

### 6. Value-Based Entity Matching
**Issue**: Assumes positional alignment, causes false positives/negatives
**Location**: `src/validators/consistency_checker.py` lines 95-200

**Required Fix**:
```python
def _match_monetary_values(self, en_vals, de_vals, lv_vals):
    """Match monetary values by similarity, not position."""
    # Use Hungarian algorithm or greedy matching
    # Match by (amount * scale, currency) similarity
    # Flag unmatched values as missing
```

### 7. Multilingual Regex Patterns
**Issue**: Missing Latvian/German legal term patterns
**Location**: `src/extractors/entity_extractor.py` lines 58-74

**Required Additions**:
```python
LEGAL_PATTERNS = {
    # Existing patterns...
    'article_lv': r'pants\s*([0-9]+)',
    'regulation_lv': r'regulas?\s*Nr\.?\s*([0-9]+/[0-9]+)',
    'article_de': r'Artikel\s*([0-9]+)',
    'paragraph_de': r'Absatz\s*([0-9]+)',
}
```

### 8. Main.py Semantic Alignment Option
**Issue**: No way to use embedding-based alignment
**Location**: `main.py` - currently only uses SimpleAligner

**Required Fix**:
```python
parser.add_argument(
    "--alignment",
    choices=['simple', 'semantic'],
    default='simple',
    help="Alignment strategy"
)

if args.alignment == 'semantic':
    from src.alignment.embeddings import EmbeddingGenerator
    from src.alignment.paragraph_aligner import ParagraphAligner
    generator = EmbeddingGenerator(use_watson=True)
    aligner = ParagraphAligner(generator)
else:
    from src.alignment.simple_aligner import SimpleAligner
    aligner = SimpleAligner()
```

### 9. Unused Dependencies
**Issue**: requirements.txt includes python-docx, pandas (unused)

**Required Fix**:
```bash
# Remove from requirements.txt:
python-docx>=1.1.0  # Not used
pandas>=2.0.0       # Not used
```

## 📊 OPTIMIZATION SUMMARY

| Issue | Severity | Status | Impact |
|-------|----------|--------|---------|
| Hardcoded credentials | 🔴 CRITICAL | ✅ FIXED | Security leak |
| Wrong embedding model | 🔴 CRITICAL | ✅ FIXED | Poor multilingual performance |
| Index mismatch bug | 🔴 CRITICAL | ⚠️ TODO | Wrong paragraph matches |
| Missing paragraph detection | 🔴 CRITICAL | ⚠️ TODO | Silently drops differences |
| Stale cache | 🟡 HIGH | ⚠️ TODO | Wrong results after changes |
| Positional entity matching | 🟡 HIGH | ⚠️ TODO | False positives/negatives |
| Missing multilingual patterns | 🟡 HIGH | ⚠️ TODO | Low recall on Latvian/German |
| No semantic alignment option | 🟡 HIGH | ⚠️ TODO | Can't use embeddings |
| Unused dependencies | 🟢 LOW | ⚠️ TODO | Bloat |

## 🎯 PRIORITY ACTIONS

**For immediate deployment:**
1. ✅ Security fix (credentials) - DONE
2. ✅ Embedding model fix - DONE
3. ⚠️ Fix index mismatch bug - TODO (30 min)
4. ⚠️ Fix SimpleAligner paragraph detection - TODO (15 min)

**For production readiness:**
5. Add versioned cache (1 hour)
6. Implement value-based matching (2 hours)
7. Add multilingual patterns (30 min)
8. Add semantic alignment CLI option (30 min)

**For cleanup:**
9. Remove unused dependencies (5 min)
10. Update documentation (30 min)

## 📝 TEST PLAN

After fixes, test:
1. Run with missing credentials → should fail gracefully
2. Run with Watson → should use Granite multilingual model
3. Run with documents of different lengths → should detect missing paragraphs
4. Run twice with same docs → should reuse cache
5. Change model → should regenerate embeddings
6. Compare simple vs semantic alignment → document differences

## 🚀 NEXT STEPS

1. Apply remaining critical fixes (#3, #4)
2. Test end-to-end with Watson credentials
3. Generate new test results
4. Update documentation to match code
5. Create PR with all fixes

---

**Time Estimate**:
- Critical fixes remaining: ~45 minutes
- Full optimization: ~5 hours
- Current progress: ~20% complete
