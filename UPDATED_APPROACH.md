# Updated Implementation Approach

## Key Changes Based on IBM Feedback

### ✅ **What We Learned:**

1. **Goal**: Find factual differences paragraph-by-paragraph
2. **Input**: Use provided JSON structure (don't re-parse .docx)
3. **Alignment**: Use embeddings for matching paragraphs across languages
4. **Output**: List of differences (JSON + Excel)
5. **Priority**: Avoid false negatives (better to flag 200 when there are 100 errors)
6. **Critical**: References and monetary values matter most
7. **Ignore**: Date format variations (16/06 vs 2023-06-16 is OK)
8. **Detect**: Missing values (specific date vs "in 2 weeks")

### 🔧 **Technology Stack:**

- **Watson AI**: For embeddings and optional LLM validation
- **Local Processing**: For rule-based validation (faster, cheaper)
- **EU Style Guide**: https://style-guide.europa.eu/en/ for validation rules

---

## Revised Solution Architecture

```
INPUT
├── test_sample_en_parsed.json
├── test_sample_de_parsed.json
└── test_sample_lv_parsed.json

STEP 1: Load JSON (Local)
├── Parse existing JSON structure
└── Extract paragraphs with para_number

STEP 2: Generate Embeddings (Watson AI)
├── Send all paragraphs to watsonx.ai Embeddings API
├── Get vector representations
└── Store embeddings for reuse

STEP 3: Align Paragraphs (Local)
├── Calculate cosine similarity between embeddings
├── Match EN ↔ DE ↔ LV paragraphs
└── Handle missing/extra/reordered paragraphs

STEP 4: Extract Entities (Local)
├── Dates: regex + parsing
├── Monetary values: amounts + currencies
├── Legal references: regulations, articles, cases
└── Normalize for comparison

STEP 5: Validate Consistency (Local)
├── Compare monetary values (CRITICAL - must be exact)
├── Compare legal references (CRITICAL - must be exact)
├── Compare dates (ignore format, check actual date)
├── Detect missing/vague values
└── Flag ALL suspicious differences

STEP 6: Optional LLM Check (Watson AI)
├── For ambiguous cases only
├── Ask: "Are these semantically equivalent?"
└── Get confidence scores

OUTPUT
├── differences.json (programmatic access)
└── differences.xlsx (human review)
```

---

## Detection Rules (Priority Order)

### 🔴 **CRITICAL (Must Never Miss)**

1. **Monetary Value Differences**
   ```
   EN: EUR 135 million
   DE: 136 Mio. EUR
   → FLAG: Different amounts (135 vs 136)
   ```

2. **Currency Mismatches**
   ```
   EN: EUR 1500 million
   DE: 1,5 Mrd USD
   → FLAG: Different currency (EUR vs USD)
   ```

3. **Scale Errors**
   ```
   EN: EUR 1,500 million
   LV: 1,500 miljardi EUR
   → FLAG: Scale error (million vs billion)
   ```

4. **Legal Reference Errors**
   ```
   EN: Regulation (EU) 2022/947
   DE: Regulation (EU) 2021/947
   → FLAG: Different regulation number
   ```

5. **Article/Paragraph Reference Errors**
   ```
   EN: Article 19(2)
   DE: Article 19(3)
   → FLAG: Different article subsection
   ```

6. **Missing Specific Values**
   ```
   EN: "on 18 March 2025"
   LV: "in two weeks"
   → FLAG: Missing specific date in LV
   ```

### 🟡 **MEDIUM (Flag if Different)**

7. **Date Value Differences**
   ```
   EN: 16/06/2023
   DE: 15/06/2023
   → FLAG: Different dates (even if format acceptable)
   ```

8. **Numerical Precision Differences**
   ```
   EN: 0.32
   DE: 0.3
   → FLAG: Potentially different values (could be rounding)
   ```

9. **Case Number Differences**
   ```
   EN: C-785/22 P
   DE: C-786/22 P
   → FLAG: Different case numbers
   ```

### ✅ **ACCEPTABLE (Don't Flag)**

10. **Date Format Variations** (same date, different format)
    ```
    EN: 16/06/2023
    DE: 16.06.2023
    LV: 2023-06-16
    → OK: Same date (2023-06-16)
    ```

11. **Number Format Variations** (same value, different separator)
    ```
    EN: 1,500
    DE: 1.500
    LV: 1 500
    → OK: Same value (1500)
    ```

12. **Translation Equivalents**
    ```
    EN: million
    DE: Mio.
    LV: miljonu
    → OK: Standard translation
    ```

---

## Implementation Plan

### Phase 1: Setup ✅
- [x] Analyze test data structure
- [x] Research Watson AI capabilities
- [ ] Set up watsonx.ai credentials
- [ ] Install `ibm-watsonx-ai` SDK

### Phase 2: Paragraph Alignment
- [ ] Load JSON files
- [ ] Generate embeddings via Watson AI
- [ ] Implement cosine similarity matching
- [ ] Test alignment accuracy on sample data

### Phase 3: Entity Extraction
- [ ] Build regex patterns for:
  - Dates (all formats)
  - Monetary values + currencies
  - Legal references (regulations, articles)
  - Case citations
- [ ] Normalize extracted entities
- [ ] Test extraction accuracy

### Phase 4: Validation Engine
- [ ] Implement monetary value comparator
- [ ] Implement legal reference validator
- [ ] Implement date comparator (format-agnostic)
- [ ] Implement missing value detector
- [ ] Add EU Style Guide rules

### Phase 5: Output Generation
- [ ] Generate JSON difference report
- [ ] Generate Excel spreadsheet (like errors_test_file.xlsx)
- [ ] Add severity levels (CRITICAL/MEDIUM/LOW)
- [ ] Add confidence scores

### Phase 6: Evaluation
- [ ] Compare output against errors_test_file.xlsx
- [ ] Calculate precision/recall
- [ ] Tune to prefer false positives
- [ ] Iterate based on feedback

---

## Expected Output Format

### JSON Format
```json
{
  "metadata": {
    "documents": ["test_sample_en", "test_sample_de", "test_sample_lv"],
    "total_differences": 41,
    "timestamp": "2025-10-29T12:00:00Z"
  },
  "differences": [
    {
      "id": 1,
      "paragraph_id": "(12)",
      "aligned_paragraphs": {
        "en": 11,
        "de": 11,
        "lv": 11
      },
      "type": "DATE_VALUE_MISMATCH",
      "severity": "MEDIUM",
      "values": {
        "en": "16/06/2023",
        "de": "15/06/2023",
        "lv": "16/06/2023"
      },
      "description": "Date value differs in German version",
      "confidence": 0.99
    },
    {
      "id": 2,
      "paragraph_id": "(29)",
      "aligned_paragraphs": {
        "en": 13,
        "de": 13,
        "lv": 13
      },
      "type": "CURRENCY_MISMATCH",
      "severity": "CRITICAL",
      "values": {
        "en": "EUR 1500 million",
        "de": "1,5 Mrd USD",
        "lv": "1500 miljonu EUR"
      },
      "description": "Currency differs: EUR vs USD in German version",
      "confidence": 1.0
    }
  ]
}
```

### Excel Format
Match the structure of `errors_test_file.xlsx`:

| Paragraph | EN | DE | LV | Type | Severity |
|-----------|----|----|----|---------| ---------|
| (12) | 16/06/2023 | 15/06/2023 | 16/06/2023 | DATE_VALUE | MEDIUM |
| (26) | 0.32 | 0.3 | 0.3 | NUMERIC | MEDIUM |
| (29) | EUR 1500 million | 1,5 Mrd USD | 1500 miljonu EUR | CURRENCY | CRITICAL |

---

## Watson AI Usage Strategy

### Use Watson AI For:
1. **Embeddings** (Primary)
   - Generate once, reuse many times
   - Enable semantic paragraph alignment
   - Handle reordered/missing paragraphs

2. **Ambiguous Cases** (Optional)
   - When rule-based logic is uncertain
   - Ask LLM: "Is this a real difference or translation variation?"
   - Example: "Mrd." could mean million or billion depending on language

### Don't Use Watson AI For:
1. **Exact Matches** (use local comparison)
2. **Simple Regex** (dates, numbers, references)
3. **Known Patterns** (use EU Style Guide rules)

**Cost-Benefit**: Embeddings are cheap, LLM calls are expensive. Use LLMs sparingly.

---

## Success Criteria

✅ **Must achieve:**
1. Detect all 41 errors in `errors_test_file.xlsx`
2. Flag additional suspicious patterns (prefer false positives)
3. Zero false negatives on CRITICAL errors (monetary, legal references)
4. Clear, actionable output format

📊 **Target Metrics:**
- Recall (find known errors): **100%** for CRITICAL, **>95%** overall
- Precision: **>50%** (OK to have false positives)
- Processing time: **<1 minute** for 3 documents

---

## Questions for IBM Team

### Technical Setup
1. ✅ Do you have watsonx.ai credentials ready?
2. ✅ What's the project_id or space_id we should use?
3. ✅ Which embedding model is recommended? (`ibm/slate-125m-english-rtrvr`?)

### Requirements Clarification
4. ✅ Should we flag formatting differences in numbers (commas vs periods)?
5. ✅ What tolerance for numerical differences? (0.32 vs 0.3 - flag or ignore?)
6. ✅ Should we validate that referenced regulations actually exist?

### Output & Workflow
7. ✅ Output format preference: JSON, Excel, or both?
8. ✅ Should we include confidence scores?
9. ✅ Do you want automated fixes suggested, or just detection?

### Testing & Evaluation
10. ✅ Are there more test documents beyond these 3 samples?
11. ✅ Will you provide feedback on false positives vs true errors?
12. ✅ What's the deadline for the hackathon submission?

---

## Resources

- **EU Style Guide**: https://style-guide.europa.eu/en/
- **Watson AI SDK**: https://ibm.github.io/watsonx-ai-python-sdk/
- **Project Docs**: See `WATSON_AI_GUIDE.md` for detailed examples
