# IBM Hackathon Test Data Analysis

## 1. Input Format

### Source Documents (`.docx` files)
The input consists of **Word documents** containing legal/regulatory text in three languages:
- **English**: `test_sample_en.docx` (65 paragraphs)
- **German**: `test_sample_de.docx` (65 paragraphs)
- **Latvian**: `test_sample_lv.docx` (64 paragraphs)

The documents contain EU regulatory text about the "Reform and Growth Facility for the Republic of Moldova" including:
- Regulation headers and metadata
- Numbered recitals (e.g., "(1)", "(3)", "(12)", etc.)
- Articles with subsections
- Legal case references
- Footnotes with citations

## 2. Expected Output Format

### Parsed JSON Structure (`*_parsed.json` files)
The output is a **JSON array** with the following structure:

```json
[
  {
    "file": "test_sample_XX.docx",
    "para": [
      {
        "para": "paragraph text content\n",
        "para_number": 1
      },
      {
        "para": "next paragraph text\n",
        "para_number": 2
      }
    ]
  }
]
```

**Key characteristics:**
- Each paragraph is sequentially numbered starting from 1
- Text content preserves newlines (`\n`)
- All paragraphs are extracted, including headers, body text, and footnotes
- Empty paragraphs are typically skipped

## 3. Types of Inconsistencies to Detect

Based on the error file analysis, the inconsistencies fall into several categories:

### A. **Numerical Inconsistencies**
- **Dates**: Different dates across translations (e.g., EN: 16/06/2023, DE: 15/06/2023)
- **Date formats**: Inconsistent formatting (e.g., "2019-07-20" vs "20/6/2019")
- **Decimal numbers**: Different precision or values (e.g., EN: 0.32, DE: 0.3, LV: 0.3)
- **Amounts**: Different currency values (e.g., EN: 389951,44 vs DE: 389952,44)
- **Large numbers**: Scale errors (e.g., "billion" vs "million" - LV: "1 500 miljardi EUR" = 1.5 trillion instead of million)

### B. **Legal Reference Errors**
- **Regulation numbers**: Wrong EU regulation number (e.g., EN: "(EU) 2022/947", DE/LV: "(EU) 2021/947")
- **Article references**: Wrong article numbers (e.g., EN: "Art 19(2)", DE: "Art 19(3)")
- **Legal prefixes**: Wrong language-specific prefixes (e.g., "(EU)" vs "(ER)" vs "(ES)")
- **Paragraph references**: Wrong internal references (e.g., EN: "Paragraph 6", DE: "Paragraph 5")

### C. **Citation/Case Reference Errors**
- **Case numbers**: Wrong case identifiers (e.g., EN: "C-785/22 P", DE: "C-786/22 P")
- **ECLI identifiers**: Inconsistent legal identifiers (e.g., "EU:T:2022:638" vs "EU:T:2022:637")
- **Paragraph numbers**: Wrong paragraph references (e.g., "31, 34 and 35" vs "31, 33 und 35")

### D. **Typographical Errors**
- **Typos in legal terms**: (e.g., EN: "(EU,Eurato)" should be "(EU,Euratom)")
- **Missing text**: (e.g., EN has "TOBEDEFINED" instead of actual article reference)
- **Extra spaces or formatting differences**

### E. **Translation-Specific Errors**
- **Currency format inconsistencies**: (e.g., "EUR 1500 million" vs "1,5 Mrd USD" vs "1500 miljonu EUR")
- **Missing percentage sign**: (e.g., DE: "0.5" missing context, shown in only DE/LV)

### F. **Structural Inconsistencies**
- **Missing sections**: Some paragraphs might be missing in certain language versions
- **Different paragraph counts**: English has 65 paragraphs, Latvian has 64

## 4. What the Error File Shows

The `errors_test_file.xlsx` serves as a **ground truth error catalog** with the following structure:

**Columns:**
- **Column A (Paragraph)**: The paragraph identifier where the error occurs (e.g., "(12)", "(26)", "(28)3")
- **Column B (EN)**: The incorrect value in the English version (or correct value for comparison)
- **Column C (DE)**: The incorrect value in the German version (or correct value for comparison)
- **Column D (LV)**: The incorrect value in the Latvian version (or correct value for comparison)

**Key insights:**
- **41 error instances** documented across the three language versions
- Errors are indexed by paragraph number (sometimes with sub-indices like "(28)3" for multiple errors in same paragraph)
- Empty cells indicate that version is correct (or the error doesn't apply)
- Each row typically shows where the inconsistency exists across the three languages

**Error distribution patterns:**
1. Some errors affect only one language (e.g., EN has wrong regulation number)
2. Some errors affect two languages (e.g., DE/LV have different value than EN)
3. Some paragraphs have multiple errors (indicated by sub-indices)

## 5. Initial Observations

### Document Characteristics
1. **Legal/regulatory documents**: High precision required for dates, numbers, and legal references
2. **Multi-lingual translations**: Three languages must be perfectly aligned
3. **Complex structure**: Nested numbering, cross-references, citations, footnotes
4. **High error density**: 41+ errors in ~65 paragraphs = significant quality control needed

### Error Patterns
1. **Systematic vs. random errors**:
   - Systematic: Wrong regulation number "(EU) 2022/947" vs correct "(EU) 2021/947"
   - Random: Typos like "(Eurato)" instead of "(Euratom)"

2. **Critical vs. minor errors**:
   - Critical: Wrong legal references, wrong amounts, scale errors (million vs billion)
   - Minor: Date format inconsistencies, minor numerical differences

3. **Language-specific issues**:
   - Different date formats per language
   - Currency abbreviations (EUR, Mio., million)
   - Legal terminology prefixes vary by language

### Data Quality Issues
1. **Paragraph count mismatch**: EN/DE have 65 paragraphs, LV has 64
2. **Missing content**: EN paragraph (44) has "TOBEDEFINED" placeholder
3. **Inconsistent formatting**: Number formats vary (commas vs periods, spacing)

## 6. Suggested Solution Pipeline

### Phase 1: Document Parsing & Normalization
```
Input: .docx files
↓
1. Extract text preserving structure (paragraphs, numbering)
2. Parse into JSON format with para_number
3. Normalize whitespace while preserving semantic line breaks
↓
Output: *_parsed.json files
```

### Phase 2: Entity Extraction & Alignment
```
Input: Parsed JSON files
↓
1. Extract entities from each paragraph:
   - Dates (various formats)
   - Numbers (decimals, percentages, amounts)
   - Legal references (regulations, articles, cases)
   - Citations (ECLI, case numbers)
   - Currency values
2. Normalize entities to canonical forms
3. Align paragraphs across the three language versions
↓
Output: Aligned entities per paragraph
```

### Phase 3: Cross-Language Consistency Checking
```
Input: Aligned entities
↓
For each aligned paragraph group:
1. Compare numerical values (exact match required)
2. Compare dates (after normalization)
3. Compare legal references (accounting for language variations)
4. Compare structural elements (paragraph counts, references)
5. Flag inconsistencies with confidence scores
↓
Output: Detected inconsistencies
```

### Phase 4: Error Classification & Reporting
```
Input: Detected inconsistencies
↓
1. Classify errors by type:
   - Numerical mismatch
   - Date inconsistency
   - Legal reference error
   - Citation error
   - Typographical error
   - Structural mismatch
2. Rank by severity (critical vs. minor)
3. Generate error report matching ground truth format
↓
Output: errors_detected.xlsx (comparable to errors_test_file.xlsx)
```

### Recommended Technology Stack

**Parsing:**
- `python-docx` for Word document parsing
- `json` for structured output

**Entity Extraction:**
- **Regex patterns** for dates, numbers, legal references
- **NER (Named Entity Recognition)** using spaCy or custom models
- **Fuzzy matching** (e.g., `fuzzywuzzy`) for near-matches

**Alignment:**
- **Paragraph alignment** via sequential numbering
- **Content-based alignment** using semantic similarity (optional: sentence transformers)

**Validation:**
- **Rule-based validators** for each entity type
- **Cross-reference checker** for internal document references
- **Statistical analysis** for numerical consistency

**Output:**
- `openpyxl` or `pandas` for Excel generation
- Structured JSON for programmatic access

### Key Challenges to Address

1. **Language-specific variations**:
   - Solution: Build language-aware normalization (e.g., "Mio." = "million" = "miljonu")

2. **Paragraph alignment when counts differ**:
   - Solution: Use content-based alignment with sequence matching algorithms

3. **Context-dependent validation**:
   - Solution: Some differences may be valid (e.g., currency format preferences)
   - Need to distinguish translation variations from actual errors

4. **Ambiguous references**:
   - Solution: Maintain cross-reference graph of internal document structure

5. **Incomplete ground truth**:
   - Solution: The error file shows known errors, but there may be additional ones
   - Build validators that can detect novel error types

### Success Metrics

The solution should:
1. **Detect all 41+ errors** documented in `errors_test_file.xlsx`
2. **Minimize false positives** (valid translation variations flagged as errors)
3. **Provide clear error descriptions** (what's wrong, where, why)
4. **Scale to larger documents** (these are small samples)
5. **Generate reports** in comparable format to ground truth

### Next Steps

1. Implement document parser (Phase 1)
2. Build entity extractors with test cases (Phase 2)
3. Create alignment algorithm (Phase 3)
4. Develop validation rules for each error type (Phase 3)
5. Test against ground truth and iterate (Phase 4)
6. Optimize for performance and accuracy
