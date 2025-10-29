"""
Streamlit UI for multilingual legal document validation.
Professional design with modern styling.
"""
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Legal Document Validator",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern professional styling
st.markdown("""
<style>
    :root {
        --blue-darkest: #0f172a;
        --blue-deep: #1e3a8a;
        --blue-primary: #1d4ed8;
        --blue-mid: #2563eb;
        --blue-light: #60a5fa;
        --blue-soft: #dbeafe;
        --blue-very-light: #eef2ff;
        --slate-900: #111827;
        --slate-700: #334155;
        --slate-500: #64748b;
    }

    /* Main background */
    .main {
        background-color: var(--blue-very-light);
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #f1f5ff;
        border-right: 1px solid var(--blue-soft);
    }

    [data-testid="stSidebar"] h2 {
        color: var(--blue-darkest);
        font-size: 1.1rem;
        font-weight: 600;
        margin-top: 1rem;
    }

    /* Button styling */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
        border: 1px solid rgba(29, 78, 216, 0.35);
        font-size: 1rem;
        padding: 0.6rem 1rem;
        background: linear-gradient(135deg, var(--blue-deep), var(--blue-primary));
        color: #ffffff;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 30px rgba(29, 78, 216, 0.25);
    }

    /* Language column cards */
    .lang-column {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
        min-height: 280px;
        border: 1px solid rgba(29, 78, 216, 0.12);
        margin-bottom: 1rem;
    }

    .lang-column-header {
        color: var(--blue-darkest);
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding-bottom: 0.75rem;
        border-bottom: 2px solid rgba(29, 78, 216, 0.12);
    }

    /* Paragraph text */
    .paragraph-text {
        color: var(--slate-700);
        font-size: 0.95rem;
        line-height: 1.8;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
        margin-top: 1rem;
    }

    /* Highlighting */
    .error-highlight {
        background-color: rgba(37, 99, 235, 0.16);
        color: var(--blue-deep);
        padding: 3px 6px;
        border-radius: 4px;
        font-weight: 500;
        border-bottom: 2px solid rgba(29, 78, 216, 0.35);
    }

    .match-highlight {
        background-color: rgba(96, 165, 250, 0.16);
        color: var(--blue-primary);
        padding: 3px 6px;
        border-radius: 4px;
        font-weight: 500;
        border-bottom: 2px solid rgba(59, 130, 246, 0.35);
    }

    /* Value display */
    .value-badge {
        background-color: #f4f7ff;
        color: var(--blue-darkest);
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-family: 'Courier New', monospace;
        display: inline-block;
        margin-top: 0.75rem;
        border: 1px solid rgba(29, 78, 216, 0.18);
        font-weight: 500;
    }

    .value-badge.error {
        background-color: rgba(29, 78, 216, 0.14);
        color: var(--blue-deep);
        border-color: rgba(29, 78, 216, 0.32);
    }

    .value-badge.missing {
        background-color: rgba(15, 23, 42, 0.08);
        color: var(--blue-darkest);
        border-color: rgba(15, 23, 42, 0.18);
    }

    /* Error type badges */
    .error-type-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .severity-badge {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
    }

    /* Error description card */
    .error-description {
        background: linear-gradient(135deg, rgba(29, 78, 216, 0.14), rgba(59, 130, 246, 0.18));
        padding: 1.25rem 1.5rem;
        border-radius: 10px;
        border-left: 4px solid var(--blue-primary);
        margin: 1.5rem 0;
        color: var(--blue-deep);
        font-size: 0.95rem;
        line-height: 1.6;
    }

    .error-description strong {
        color: var(--blue-darkest);
        font-weight: 600;
    }

    /* Header styling */
    .app-header {
        background: linear-gradient(135deg, var(--blue-darkest) 0%, var(--blue-primary) 100%);
        padding: 2rem 2.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .app-header h1 {
        color: white;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
    }

    .app-header p {
        color: rgba(255,255,255,0.95);
        font-size: 1.1rem;
        margin: 0;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--blue-darkest);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.9rem;
        color: var(--slate-500);
        font-weight: 500;
    }

    /* Navigation */
    .nav-section {
        background: #ffffff;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
        margin-bottom: 1.5rem;
        border: 1px solid rgba(29, 78, 216, 0.12);
    }

    /* Validation section */
    .validation-section {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
        margin-top: 1.5rem;
        border: 1px solid rgba(29, 78, 216, 0.12);
    }

    .validation-title {
        color: var(--blue-darkest);
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 1rem;
    }

    /* Status indicators */
    .status-icon {
        font-size: 1.2rem;
        margin-right: 0.25rem;
    }

    /* Caption text */
    .caption-text {
        color: var(--slate-500);
        font-size: 0.85rem;
        margin-top: 0.75rem;
        font-style: italic;
    }

    /* Divider */
    hr {
        border: none;
        border-top: 1px solid rgba(29, 78, 216, 0.12);
        margin: 1.5rem 0;
    }

    /* Info box */
    .info-box {
        background-color: rgba(37, 99, 235, 0.12);
        border-left: 4px solid var(--blue-deep);
        padding: 1rem 1.25rem;
        border-radius: 8px;
        color: var(--blue-deep);
        font-size: 0.9rem;
        margin-top: 1rem;
    }

    /* Metadata card */
    .metadata-card {
        background: #ffffff;
        padding: 1.25rem 1.5rem;
        border-radius: 10px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
        border: 1px solid rgba(29, 78, 216, 0.12);
        margin-bottom: 1.5rem;
    }

    /* Summary section */
    .summary-section {
        margin-bottom: 2rem;
    }

    .summary-grid {
        display: grid;
        gap: 1.25rem;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        margin-bottom: 1.5rem;
    }

    .summary-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 14px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        border: 1px solid rgba(37, 99, 235, 0.15);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
        overflow: hidden;
    }

    .summary-card::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(29, 78, 216, 0.18));
        opacity: 0;
        transition: opacity 0.3s ease;
        pointer-events: none;
    }

    .summary-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 18px 40px rgba(15, 23, 42, 0.15);
    }

    .summary-card:hover::after {
        opacity: 1;
    }

    .summary-icon {
        font-size: 1.8rem;
        margin-bottom: 0.75rem;
    }

    .summary-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--slate-500);
        font-weight: 700;
        margin-bottom: 0.35rem;
    }

    .summary-value {
        font-size: 2.15rem;
        font-weight: 700;
        color: var(--slate-900);
        margin-bottom: 0.4rem;
    }

    .summary-caption {
        font-size: 0.9rem;
        color: var(--slate-500);
        font-weight: 500;
    }

    .pill-bar {
        display: inline-flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-top: 0.75rem;
    }

    .pill {
        padding: 4px 12px;
        border-radius: 999px;
        background: rgba(29, 78, 216, 0.15);
        color: var(--blue-deep);
        font-size: 0.8rem;
        font-weight: 600;
    }

    .severity-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 14px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        border: 1px solid rgba(37, 99, 235, 0.15);
    }

    .severity-heading {
        font-size: 1rem;
        font-weight: 600;
        color: var(--blue-darkest);
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .severity-row {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 0.85rem;
    }

    .severity-label {
        width: 120px;
        font-weight: 600;
        font-size: 0.9rem;
        color: var(--slate-700);
    }

    .severity-track {
        flex: 1;
        height: 10px;
        background: rgba(148, 163, 184, 0.25);
        border-radius: 999px;
        overflow: hidden;
    }

    .severity-fill {
        height: 100%;
        border-radius: 999px;
    }

    .severity-critical { background: var(--blue-darkest); }
    .severity-high { background: var(--blue-deep); }
    .severity-medium { background: var(--blue-primary); }
    .severity-low { background: rgba(59, 130, 246, 0.45); }

    .severity-count {
        width: 42px;
        text-align: right;
        font-weight: 600;
        color: var(--blue-darkest);
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    """Load differences and paragraph data."""
    # Load differences
    with open('output/differences.json', 'r') as f:
        data = json.load(f)

    # Load parsed documents
    docs = {}
    for lang in ['en', 'de', 'lv']:
        path = f'data/test_sample_{lang}_parsed.json'
        with open(path, 'r') as f:
            parsed = json.load(f)
            # Create dict mapping para_number to para text
            docs[lang] = {p['para_number']: p['para'] for p in parsed[0]['para']}

    return data['differences'], data['metadata'], docs


def get_error_type_badge(error_type: str) -> str:
    """Generate colored badge for error type."""
    colors = {
        'DATE_VALUE': '#1e3a8a',
        'MONETARY_VALUE': '#0f172a',
        'LEGAL_REFERENCE': '#312e81',
        'ARTICLE_REFERENCE': '#1d4ed8',
        'MISSING_VALUE': '#111827',
        'CURRENCY_MISMATCH': '#2563eb',
        'SCALE_ERROR': '#4338ca',
        'MISSING_PARAGRAPH': '#0f172a'
    }
    color = colors.get(error_type, '#1d4ed8')
    return f'<span class="error-type-badge" style="background:{color}">{error_type.replace("_", " ")}</span>'


def get_severity_badge(severity: str) -> str:
    """Generate colored badge for severity."""
    colors = {
        'CRITICAL': '#0f172a',
        'HIGH': '#1e3a8a',
        'MEDIUM': '#1d4ed8',
        'LOW': '#60a5fa'
    }
    color = colors.get(severity, '#1d4ed8')
    return f'<span class="severity-badge" style="background:{color}">{severity}</span>'


def highlight_text(text: str, highlight_value: str, is_error: bool = True) -> str:
    """
    Highlight specific text within a paragraph.

    Args:
        text: Full paragraph text
        highlight_value: The value to highlight
        is_error: Whether this is an error (red) or match (yellow)

    Returns:
        HTML formatted text with highlighting
    """
    if highlight_value == "MISSING":
        return text

    # Escape HTML
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    highlight_value = highlight_value.replace('<', '&lt;').replace('>', '&gt;')

    # Apply highlighting
    css_class = "error-highlight" if is_error else "match-highlight"
    highlighted = text.replace(
        highlight_value,
        f'<span class="{css_class}">{highlight_value}</span>'
    )

    return highlighted


def get_paragraph_text(docs: Dict, lang: str, para_id: Optional[int]) -> str:
    """Get paragraph text for a given language and paragraph ID."""
    if para_id is None or para_id not in docs[lang]:
        return "[Paragraph not found]"
    return docs[lang][para_id]


def should_highlight_as_error(diff: Dict, lang: str) -> bool:
    """
    Determine if a value should be highlighted as an error for a given language.

    For MISSING_VALUE errors: the non-missing language is the error.
    For other errors: all non-MISSING values are errors.
    """
    values = diff['values']

    if diff['error_type'] == 'MISSING_VALUE':
        # The language that has a value (not MISSING) is the error
        return values[lang] != "MISSING"
    else:
        # For mismatches, highlight all (use yellow for context)
        return False


def display_language_column(lang: str, lang_name: str, flag: str, diff: Dict, docs: Dict):
    """Display a single language column with paragraph text and value."""
    para_ids = diff['paragraph_ids']
    value = diff['values'][lang]

    # Get paragraph text
    para_text = get_paragraph_text(docs, lang, para_ids[lang])

    # Determine if this should be highlighted
    is_error = should_highlight_as_error(diff, lang)

    # Build HTML
    html = f'<div class="lang-column">'
    html += f'<div class="lang-column-header">{flag} {lang_name}</div>'

    # Paragraph text with highlighting
    if value != "MISSING":
        highlighted = highlight_text(para_text, value, is_error)
        html += f'<div class="paragraph-text">{highlighted}</div>'
    else:
        escaped_text = para_text.replace('<', '&lt;').replace('>', '&gt;')
        html += f'<div class="paragraph-text">{escaped_text}</div>'

    # Value badge
    if value == "MISSING":
        badge_class = "value-badge missing"
        status = "⚠️"
    elif diff['error_type'] == 'MISSING_VALUE' and value != "MISSING":
        badge_class = "value-badge error"
        status = "❌"
    else:
        badge_class = "value-badge"
        status = "✓"

    html += f'<div class="{badge_class}">{status} {value}</div>'
    html += '</div>'

    st.markdown(html, unsafe_allow_html=True)


def display_error(diff: Dict, docs: Dict, current_idx: int, total: int):
    """Display a single error with side-by-side comparison."""

    # Metadata card
    st.markdown('<div class="metadata-card">', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        st.markdown(f"**Error Type**<br/>{get_error_type_badge(diff['error_type'])}",
                   unsafe_allow_html=True)
    with col2:
        st.markdown(f"**Severity**<br/>{get_severity_badge(diff['severity'])}",
                   unsafe_allow_html=True)
    with col3:
        st.metric("Confidence", f"{diff['confidence']:.0%}")
    with col4:
        st.metric("Position", f"{current_idx + 1}/{total}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Three-column layout for languages
    col_en, col_de, col_lv = st.columns(3)

    with col_en:
        display_language_column('en', 'English', '🇬🇧', diff, docs)

    with col_de:
        display_language_column('de', 'German', '🇩🇪', diff, docs)

    with col_lv:
        display_language_column('lv', 'Latvian', '🇱🇻', diff, docs)

    # Error description
    st.markdown(f'<div class="error-description"><strong>Issue:</strong> {diff["description"]}</div>',
                unsafe_allow_html=True)

    # Paragraph reference
    para_ids = diff['paragraph_ids']
    st.markdown(f'<div class="caption-text">📄 Paragraph IDs: EN={para_ids["en"]}, DE={para_ids["de"]}, LV={para_ids["lv"]}</div>',
               unsafe_allow_html=True)


def render_summary_card(title: str, value: str, caption: str, icon: str) -> None:
    """Render a single summary card."""
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="summary-icon">{icon}</div>
            <div class="summary-title">{title}</div>
            <div class="summary-value">{value}</div>
            <div class="summary-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_summary(differences: List[Dict]) -> None:
    """Render top-level overview metrics and severity breakdown."""
    total = len(differences)
    severity_counts = Counter(d['severity'] for d in differences)
    avg_confidence = (
        sum(d.get('confidence', 0.0) for d in differences) / total
        if total else 0.0
    )
    monetary_alerts = sum(1 for d in differences if d['error_type'] == 'MONETARY_VALUE')

    icon_map = {
        'CRITICAL': '🚨',
        'HIGH': '⚠️',
        'MEDIUM': '🟡',
        'LOW': 'ℹ️'
    }
    severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

    st.markdown('<div class="summary-section">', unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        render_summary_card(
            "AI Predictions",
            f"{total:,}",
            "Detected by machine learning model",
            "🤖"
        )
    with cols[1]:
        critical = severity_counts.get('CRITICAL', 0)
        render_summary_card(
            "High Priority",
            f"{critical}",
            "Require human validation",
            "🎯"
        )
    with cols[2]:
        render_summary_card(
            "Monetary Alerts",
            f"{monetary_alerts}",
            "Financial discrepancies flagged",
            "💶"
        )
    with cols[3]:
        render_summary_card(
            "Model Confidence",
            f"{avg_confidence:.0%}",
            "AI certainty across predictions",
            "📊"
        )

    # Severity breakdown card
    st.markdown('<div class="severity-card">', unsafe_allow_html=True)
    st.markdown(
        '<div class="severity-heading">Severity breakdown<span>Share of total findings</span></div>',
        unsafe_allow_html=True
    )

    for severity in severity_order:
        count = severity_counts.get(severity, 0)
        percentage = (count / total * 100) if total else 0
        css_class = f"severity-{severity.lower()}"
        icon = icon_map.get(severity, '•')
        st.markdown(
            f"""
            <div class="severity-row">
                <div class="severity-label">{icon} {severity.title()}</div>
                <div class="severity-track">
                    <div class="severity-fill {css_class}" style="width: {percentage:.1f}%;"></div>
                </div>
                <div class="severity-count">{count}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Show top error types as pills
    top_types = sorted(
        Counter(d['error_type'] for d in differences).items(),
        key=lambda x: x[1],
        reverse=True
    )[:4]
    if top_types:
        pills = "".join(
            f'<span class="pill">{etype.replace("_", " ").title()} · {count}</span>'
            for etype, count in top_types
        )
        st.markdown(f'<div class="pill-bar">{pills}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main application."""

    # Load data
    try:
        differences, metadata, docs = load_data()
    except FileNotFoundError as e:
        st.error(f"Error loading data: {e}")
        st.info("Please ensure output/differences.json and data/test_sample_*_parsed.json files exist.")
        return

    # Header
    st.markdown(f"""
    <div class="app-header">
        <h1>🤖 AI Document Validator</h1>
        <p>Reinforcement Learning System • Human-in-the-Loop Validation</p>
        <p style="font-size: 0.9rem; opacity: 0.9; margin-top: 0.5rem;">
            {len(differences)} inconsistencies detected • Validate to improve AI accuracy
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Add RL system explanation banner
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(29, 78, 216, 0.1), rgba(59, 130, 246, 0.15));
                border-left: 4px solid #1d4ed8;
                padding: 1.25rem 1.5rem;
                border-radius: 10px;
                margin-bottom: 2rem;
                color: #1e3a8a;">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="font-size: 2rem;">🧠</div>
            <div>
                <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 0.5rem;">
                    Reinforcement Learning System Active
                </div>
                <div style="font-size: 0.9rem; line-height: 1.6; color: #334155;">
                    This AI uses <strong>human-in-the-loop validation</strong> to improve accuracy over time.
                    Each validation you provide becomes training data, helping the model distinguish real errors from false positives.
                    <span style="color: #1d4ed8; font-weight: 500;">Your feedback directly improves future predictions.</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_summary(differences)

    # Initialize session state
    if 'current_idx' not in st.session_state:
        st.session_state.current_idx = 0
    if 'validations' not in st.session_state:
        st.session_state.validations = {}

    # Sidebar filters
    st.sidebar.markdown("## 🧠 AI Training Dashboard")

    # Add reinforcement learning explanation
    st.sidebar.info("""
    **How it works:**

    1️⃣ AI detects potential errors

    2️⃣ You validate each finding

    3️⃣ System learns from your feedback

    4️⃣ Future predictions improve
    """)

    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🔍 Filters")

    # Get unique error types and severities
    all_error_types = sorted(set(d['error_type'] for d in differences))
    all_severities = sorted(set(d['severity'] for d in differences),
                           key=lambda x: ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].index(x)
                           if x in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] else 999)

    error_type_filter = st.sidebar.multiselect(
        "Error Type",
        options=all_error_types,
        default=all_error_types
    )

    severity_filter = st.sidebar.multiselect(
        "Severity",
        options=all_severities,
        default=all_severities
    )

    # Apply filters
    filtered_diffs = [
        d for d in differences
        if d['error_type'] in error_type_filter and d['severity'] in severity_filter
    ]

    if not filtered_diffs:
        st.warning("No errors match the selected filters.")
        return

    # Ensure current index is valid
    if st.session_state.current_idx >= len(filtered_diffs):
        st.session_state.current_idx = 0

    # Progress tracking in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 📊 Training Progress")

    validated_count = len([v for v in st.session_state.validations.values() if v != "skip"])
    real_errors = len([v for v in st.session_state.validations.values() if v == "real"])
    false_positives = len([v for v in st.session_state.validations.values() if v == "false_positive"])

    # Calculate accuracy metric
    if validated_count > 0:
        accuracy = (real_errors / validated_count) * 100
    else:
        accuracy = 0

    st.sidebar.metric("Training Samples", f"{validated_count}/{len(differences)}")
    st.sidebar.progress(validated_count / len(differences) if len(differences) > 0 else 0)

    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("✓ Confirmed", real_errors)
    with col2:
        st.metric("✗ Rejected", false_positives)

    if validated_count > 0:
        st.sidebar.metric("AI Accuracy", f"{accuracy:.1f}%",
                         help="Percentage of AI predictions confirmed as real errors")

    # Export button
    st.sidebar.markdown("---")
    if st.sidebar.button("💾 Export Training Data", type="primary", use_container_width=True):
        export_data = {
            'training_data': [
                {
                    **d,
                    'validation': st.session_state.validations.get(d['id'], 'unreviewed'),
                    'feedback_label': 1 if st.session_state.validations.get(d['id']) == 'real' else 0 if st.session_state.validations.get(d['id']) == 'false_positive' else None
                }
                for d in differences
            ],
            'training_summary': {
                'total_samples': len(differences),
                'positive_labels': real_errors,
                'negative_labels': false_positives,
                'unlabeled': len(differences) - validated_count,
                'model_accuracy': accuracy if validated_count > 0 else None
            }
        }

        output_path = Path('output/training_data.json')
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        st.sidebar.success("✓ Training data exported!")

    # Main content - Navigation
    st.markdown('<div class="nav-section">', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 3, 1.5, 1.5])

    with col1:
        if st.button("⬅️ Previous", disabled=st.session_state.current_idx == 0, use_container_width=True):
            st.session_state.current_idx = max(0, st.session_state.current_idx - 1)
            st.rerun()

    with col2:
        # Jump to error
        jump_to = st.number_input(
            "Jump to",
            min_value=1,
            max_value=len(filtered_diffs),
            value=st.session_state.current_idx + 1,
            label_visibility="collapsed"
        )
        if jump_to - 1 != st.session_state.current_idx:
            st.session_state.current_idx = jump_to - 1
            st.rerun()

    with col3:
        st.markdown(f"<div style='text-align: center; padding: 8px; font-size: 1.1rem; font-weight: 600; color: #1f2937;'>Showing Error {st.session_state.current_idx + 1} of {len(filtered_diffs)}</div>",
                   unsafe_allow_html=True)

    with col5:
        if st.button("Next ➡️", disabled=st.session_state.current_idx >= len(filtered_diffs) - 1, use_container_width=True):
            st.session_state.current_idx = min(len(filtered_diffs) - 1, st.session_state.current_idx + 1)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # Display current error
    current_diff = filtered_diffs[st.session_state.current_idx]
    display_error(current_diff, docs, st.session_state.current_idx, len(filtered_diffs))

    # Validation section - Human-in-the-Loop
    st.markdown('<div class="validation-section">', unsafe_allow_html=True)
    st.markdown('''
        <div class="validation-title">
            🧠 Human-in-the-Loop Validation
            <span style="font-size: 0.85rem; font-weight: normal; color: #64748b; margin-left: 1rem;">
                Your feedback trains the AI
            </span>
        </div>
    ''', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    diff_id = current_diff['id']
    current_validation = st.session_state.validations.get(diff_id, None)

    with col1:
        if st.button("✅ Confirm Error", type="primary", use_container_width=True,
                    help="This is a real error. AI learns to detect similar patterns."):
            st.session_state.validations[diff_id] = "real"
            if st.session_state.current_idx < len(filtered_diffs) - 1:
                st.session_state.current_idx += 1
            st.rerun()

    with col2:
        if st.button("❌ Reject (False Positive)", use_container_width=True,
                    help="This is NOT an error. AI learns to avoid this pattern."):
            st.session_state.validations[diff_id] = "false_positive"
            if st.session_state.current_idx < len(filtered_diffs) - 1:
                st.session_state.current_idx += 1
            st.rerun()

    with col3:
        if st.button("⏭️ Skip for Now", use_container_width=True,
                    help="Uncertain? Skip and review later."):
            st.session_state.validations[diff_id] = "skip"
            if st.session_state.current_idx < len(filtered_diffs) - 1:
                st.session_state.current_idx += 1
            st.rerun()

    # Show current validation status with learning feedback
    if current_validation:
        status_messages = {
            "real": "✅ <strong>Confirmed:</strong> AI will strengthen detection of similar patterns",
            "false_positive": "❌ <strong>Rejected:</strong> AI will reduce false positives like this",
            "skip": "⏭️ <strong>Skipped:</strong> No training signal provided"
        }
        message = status_messages.get(current_validation, "")
        st.markdown(f'<div class="info-box">{message}</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
