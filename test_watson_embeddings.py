#!/usr/bin/env python3
"""
Test Watson AI embedding models to find the best one for multilingual documents.
"""
import os
import sys
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Import from config to use the credentials there
try:
    from config import WATSON_API_KEY, WATSON_URL, WATSON_PROJECT_ID
except ImportError:
    # Fallback to environment variables
    WATSON_API_KEY = os.getenv("WATSON_API_KEY", "")
    WATSON_URL = os.getenv("WATSON_URL", "https://us-south.ml.cloud.ibm.com")
    WATSON_PROJECT_ID = os.getenv("WATSON_PROJECT_ID", "")

# Available Watson AI embedding models
WATSON_MODELS = [
    "ibm/slate-125m-english-rtrvr",      # Best for English (768 dims)
    "ibm/slate-30m-english-rtrvr",       # Faster, smaller (384 dims)
    "ibm/granite-embedding-107m-multilingual",  # BEST FOR MULTILINGUAL
]

# Test sentences in EN, DE, LV (same meaning)
TEST_SENTENCES = {
    "en": "The facility is supported with EUR 520 million in non-repayable support.",
    "de": "Die Fazilität wird mit Mitteln in Höhe von 520 Mio. EUR an nicht rückzahlbarer Unterstützung unterstützt.",
    "lv": "Mehānismu atbalsta ar līdzekļiem 520 miljonu EUR apmērā neatmaksājama atbalsta veidā."
}


def test_watson_model(model_id: str):
    """Test a Watson AI embedding model."""
    print(f"\n{'='*70}")
    print(f"Testing: {model_id}")
    print('='*70)

    try:
        from ibm_watsonx_ai import Credentials
        from ibm_watsonx_ai.foundation_models import Embeddings

        credentials = Credentials(
            url=WATSON_URL,
            api_key=WATSON_API_KEY
        )

        model = Embeddings(
            model_id=model_id,
            credentials=credentials,
            project_id=WATSON_PROJECT_ID
        )

        # Generate embeddings
        print("Generating embeddings...")
        texts = list(TEST_SENTENCES.values())
        embeddings = model.embed_documents(texts)
        embeddings = np.array(embeddings)

        print(f"✓ Embedding shape: {embeddings.shape}")
        print(f"  Dimensions: {embeddings.shape[1]}")

        # Calculate cross-language similarity
        print("\nCross-language similarity scores:")
        en_vec = embeddings[0:1]
        de_vec = embeddings[1:2]
        lv_vec = embeddings[2:3]

        sim_en_de = cosine_similarity(en_vec, de_vec)[0][0]
        sim_en_lv = cosine_similarity(en_vec, lv_vec)[0][0]
        sim_de_lv = cosine_similarity(de_vec, lv_vec)[0][0]

        print(f"  EN ↔ DE: {sim_en_de:.4f}")
        print(f"  EN ↔ LV: {sim_en_lv:.4f}")
        print(f"  DE ↔ LV: {sim_de_lv:.4f}")
        print(f"  Average: {(sim_en_de + sim_en_lv + sim_de_lv) / 3:.4f}")

        # Higher similarity = better for multilingual alignment
        avg_similarity = (sim_en_de + sim_en_lv + sim_de_lv) / 3

        if avg_similarity > 0.8:
            print("\n✅ EXCELLENT for multilingual documents!")
        elif avg_similarity > 0.6:
            print("\n✓ GOOD for multilingual documents")
        else:
            print("\n⚠ May struggle with multilingual alignment")

        return {
            "model": model_id,
            "success": True,
            "dimensions": embeddings.shape[1],
            "avg_similarity": avg_similarity,
            "scores": {"en_de": sim_en_de, "en_lv": sim_en_lv, "de_lv": sim_de_lv}
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "model": model_id,
            "success": False,
            "error": str(e)
        }


def test_local_model():
    """Test local sentence transformer as baseline."""
    print(f"\n{'='*70}")
    print("Testing: sentence-transformers/all-MiniLM-L6-v2 (LOCAL)")
    print('='*70)

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        print("Generating embeddings...")
        texts = list(TEST_SENTENCES.values())
        embeddings = model.encode(texts)
        embeddings = np.array(embeddings)

        print(f"✓ Embedding shape: {embeddings.shape}")
        print(f"  Dimensions: {embeddings.shape[1]}")

        # Calculate cross-language similarity
        print("\nCross-language similarity scores:")
        en_vec = embeddings[0:1]
        de_vec = embeddings[1:2]
        lv_vec = embeddings[2:3]

        sim_en_de = cosine_similarity(en_vec, de_vec)[0][0]
        sim_en_lv = cosine_similarity(en_vec, lv_vec)[0][0]
        sim_de_lv = cosine_similarity(de_vec, lv_vec)[0][0]

        print(f"  EN ↔ DE: {sim_en_de:.4f}")
        print(f"  EN ↔ LV: {sim_en_lv:.4f}")
        print(f"  DE ↔ LV: {sim_de_lv:.4f}")
        print(f"  Average: {(sim_en_de + sim_en_lv + sim_de_lv) / 3:.4f}")

        avg_similarity = (sim_en_de + sim_en_lv + sim_de_lv) / 3

        return {
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "success": True,
            "dimensions": embeddings.shape[1],
            "avg_similarity": avg_similarity,
            "scores": {"en_de": sim_en_de, "en_lv": sim_en_lv, "de_lv": sim_de_lv}
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return {
            "model": "local",
            "success": False,
            "error": str(e)
        }


def main():
    """Run all tests and recommend best model."""
    print("="*70)
    print("  Watson AI Embedding Model Test")
    print("="*70)

    # Check Watson AI configuration
    if not WATSON_API_KEY or not WATSON_PROJECT_ID:
        print("\n⚠ Watson AI not configured!")
        print("\nTo test Watson AI models, set environment variables:")
        print("  export WATSON_API_KEY='your_api_key'")
        print("  export WATSON_PROJECT_ID='your_project_id'")
        print("\nTesting local model only...\n")

        # Test local model as fallback
        result = test_local_model()
        print("\n" + "="*70)
        print("✓ Local model tested. To test Watson AI, configure credentials.")
        print("="*70)
        return

    print(f"\n✓ Watson AI configured")
    print(f"  URL: {WATSON_URL}")
    print(f"  Project ID: {WATSON_PROJECT_ID[:8]}...{WATSON_PROJECT_ID[-4:]}")

    # Test all models
    results = []

    # Test Watson models
    for model_id in WATSON_MODELS:
        result = test_watson_model(model_id)
        results.append(result)

    # Test local model for comparison
    result = test_local_model()
    results.append(result)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    successful = [r for r in results if r.get("success")]

    if not successful:
        print("❌ No models tested successfully")
        return

    print("\nModel Performance Ranking:\n")
    successful.sort(key=lambda x: x.get("avg_similarity", 0), reverse=True)

    for i, result in enumerate(successful, 1):
        model_name = result["model"].split("/")[-1] if "/" in result["model"] else result["model"]
        avg_sim = result.get("avg_similarity", 0)
        dims = result.get("dimensions", 0)

        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        print(f"{medal} {model_name}")
        print(f"   Avg Similarity: {avg_sim:.4f}")
        print(f"   Dimensions: {dims}")
        print()

    # Recommendation
    best = successful[0]
    print("="*70)
    print("RECOMMENDATION")
    print("="*70)
    print(f"\n✅ Best model for your multilingual documents:\n")
    print(f"   {best['model']}")
    print(f"\n   Average similarity: {best['avg_similarity']:.4f}")
    print(f"   Embedding dimensions: {best['dimensions']}")

    print("\n" + "="*70)
    print("To use this model, update config.py:")
    print("="*70)

    if "watsonx" in best["model"] or "ibm" in best["model"]:
        print(f'\nWATSON_EMBEDDING_MODEL = "{best["model"]}"')
        print('\n# In embeddings.py, use:')
        print('self.model = Embeddings(')
        print(f'    model_id="{best["model"]}",')
        print('    credentials=credentials,')
        print('    project_id=WATSON_PROJECT_ID')
        print(')')
    else:
        print(f'\nEMBEDDING_MODEL = "{best["model"]}"')

    print("\n" + "="*70)


if __name__ == "__main__":
    main()
