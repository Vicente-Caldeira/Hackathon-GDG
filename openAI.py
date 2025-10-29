import os
import json
import argparse
from openai import OpenAI, OpenAIError

# ===== CONFIG =====

MODEL = os.getenv("OPENAI_MODEL") or "gpt-5"   # e.g., "gpt-4o-mini" to save credits
MAX_TOKENS = 1500
TEMPERATURE = 0

# ===== DEFAULT INPUTS (used only if --id not provided) =====
p1 = "(29)\tDie Fazilität sollte ..."
p2 = "(29)\tMehānisms būtu jāatbalsta ..."
p3 = "(29)\tThe Facility should be supported ..."

SYSTEM_PROMPT = (
    "You are a meticulous EU-law comparison assistant.\n"
    "Task: Given three versions of the same recital/paragraph (potentially in different languages), "
    "detect each version's language, compare factual content, and report mismatches grouped by languages that share the same values.\n\n"
    "Output format requirements (return plain text ONLY, no JSON, no extra commentary):\n"
    "1) First line: 'There were N errors detected.'\n"
    "2) For each error i starting from 1:\n"
    "   'Error i:'\n" 
    "   Then one or more lines starting with 'In Version(s): ' followed by the language name(s) (English, German, Latvian, etc.)\n"
    "   in parentheses list the differing value(s). If multiple languages share the same value, group them together.\n"
    "   Then 'Explanation: ' with a one-line explanation of the difference.\n"
    "3) End the report with a final line: '[END]'\n\n"
    "Consider and classify factual mismatches under the following categories (or use 'other' if none apply):\n"
    "- percentage, date, year_range, money, article_ref, legal_id, paragraph, ecli, case,\n"
    "- article_variants, missing_value, number, citation_format, terminology, punctuation_or_symbol,\n"
    "- unit_or_measure, range_or_period, structural_reference, other.\n\n"
    "If a version lacks a fact entirely, mark it as missing in that language’s entry. "
    "Always base differences on objective factual or numerical mismatches, not translation style.\n"
)

def build_user_prompt(v1: str, v2: str, v3: str) -> str:
    return (
        "Compare these three versions and produce the report in the exact format described:\n\n"
        f"Version 1:\n{v1}\n\n"
        f"Version 2:\n{v2}\n\n"
        f"Version 3:\n{v3}\n"
        "\nIdentify only real factual mismatches. If everything matches, say 'There were 0 errors detected.' and then print '[END]'."
    )

def run_report(api_key: str, model: str, v1: str, v2: str, v3: str) -> str:
    client = OpenAI(api_key=api_key)
    resp = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=build_user_prompt(v1, v2, v3),
    )
    return resp.output_text.strip()

# ===== JSON HELPERS (align by para_number) =====
def load_by_para_number(json_path: str) -> dict[int, str]:
    """
    Expects format:
    [
      {
        "file": "...",
        "para": [
          {"para": "...", "para_number": 1},
          ...
        ]
      }
    ]
    Returns {para_number:int -> para_text:str}
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data[0]["para"] if isinstance(data, list) and data else []
    out = {}
    for row in items:
        pn = row.get("para_number")
        if pn is None:
            continue
        try:
            key = int(pn)
        except Exception:
            continue
        out[key] = (row.get("para") or "").strip()
    return out

def get_triplet_for_id(para_id: int, path_de: str, path_lv: str, path_en: str) -> tuple[str, str, str]:
    de = load_by_para_number(path_de)
    lv = load_by_para_number(path_lv)
    en = load_by_para_number(path_en)

    missing = [name for name, m in (("DE", de), ("LV", lv), ("EN", en)) if para_id not in m]
    if missing:
        raise SystemExit(f"para_number {para_id} not found in: {', '.join(missing)}")

    return de[para_id], lv[para_id], en[para_id]

def main():
    parser = argparse.ArgumentParser(description="LLM EU-law consistency report (single paragraph by para_number).")
    parser.add_argument("--id", type=int, help="para_number to compare (aligns DE/LV/EN by this number).")
    parser.add_argument("--de", type=str, help="Path to DE JSON.")
    parser.add_argument("--lv", type=str, help="Path to LV JSON.")
    parser.add_argument("--en", type=str, help="Path to EN JSON.")
    parser.add_argument("--api-key", type=str, help="OpenAI API key override.")
    parser.add_argument("--model", type=str, help="Model override (default from OPENAI_MODEL or 'gpt-5').")

    args = parser.parse_args()

    api_key = (args.api_key or API_KEY).strip()
    if not api_key or api_key == "sk-REPLACE_ME":
        raise SystemExit("No API key set. Use OPENAI_API_KEY env var or --api-key.")

    model = args.model or MODEL

    # If an ID and all three JSONs are provided, use them; else fallback to built-in p1/p2/p3
    if args.id is not None:
        if not (args.de and args.lv and args.en):
            raise SystemExit("When using --id, you must also pass --de, --lv, and --en JSON paths.")
        v1, v2, v3 = get_triplet_for_id(args.id, args.de, args.lv, args.en)
    else:
        v1, v2, v3 = p1, p2, p3

    try:
        output = run_report(api_key, model, v1, v2, v3)
        print(output)
    except OpenAIError as e:
        msg = str(e)
        if "insufficient_quota" in msg:
            print("OpenAIError: Insufficient quota. Add billing/credits and try again.")
        elif "api_key" in msg.lower():
            print("OpenAIError: Invalid or missing API key.")
        else:
            print(f"OpenAIError: {msg}")
        raise
    except Exception as ex:
        print(f"Unexpected error: {ex}")
        raise

if __name__ == "__main__":
    main()
