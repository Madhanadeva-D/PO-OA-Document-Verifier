import streamlit as st
import pdfplumber
import tempfile
import os
from openai import OpenAI
from dotenv import load_dotenv

# ─────────────────────────────
# LOAD ENV
# ─────────────────────────────
load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    st.error("❌ API Key not found")
    st.stop()

# ─────────────────────────────
# OPENROUTER CLIENT
# ─────────────────────────────
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

MODEL = "meta-llama/llama-3.3-70b-instruct"

st.set_page_config(page_title="PO ↔ OA Verifier", layout="wide", page_icon="📑")

# ─────────────────────────────
# EXTRACT FIRST PAGE ONLY
# ─────────────────────────────
def extract_first_page(file):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.getvalue())
            path = tmp.name

        with pdfplumber.open(path) as pdf:
            if len(pdf.pages) == 0:
                return ""
            text = pdf.pages[0].extract_text() or ""

        os.unlink(path)
        return text.strip()

    except Exception as e:
        st.error(f"❌ PDF Error: {e}")
        return ""


# ─────────────────────────────
# AI COMPARISON
# ─────────────────────────────
def compare_with_ai(po_text, oa_text):
    prompt = f"""
You are a STRICT document comparison system.

Extract and compare ONLY these fields:

- po_number
- po_date
- customer_name
- delivery_address
- billing_address
- product_description
- customer_material_number

STRICT RULES:
- DO NOT guess
- EXACT match only
- If different → ❌ MISMATCH
- If same → ✅ MATCH
- If missing → ❌ MISMATCH

Return EXACT format:

OVERALL: COMPLIANT or DISCREPANCIES FOUND

| Field | PO Value | OA Value | Status |
|------|----------|----------|--------|
| po_number | ... | ... | ✅ / ❌ |
| po_date | ... | ... | ✅ / ❌ |
| customer_name | ... | ... | ✅ / ❌ |
| delivery_address | ... | ... | ✅ / ❌ |
| billing_address | ... | ... | ✅ / ❌ |
| product_description | ... | ... | ✅ / ❌ |
| customer_material_number | ... | ... | ✅ / ❌ |  

--- PURCHASE ORDER ---
{po_text[:3000]}

--- ORDER ACKNOWLEDGEMENT ---
{oa_text[:3000]}
"""

    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:8501",
                "X-OpenRouter-Title": "PO-OA-Verifier",
            },
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        return response.choices[0].message.content

    except Exception as e:
        st.error(f"❌ AI Error: {e}")
        return ""


# ─────────────────────────────
# UI
# ─────────────────────────────
st.title("📑 PO ↔ OA Document Verifier (AI Powered)")
st.caption("First page only · Strict comparison · High accuracy")

col1, col2 = st.columns(2)

with col1:
    po_file = st.file_uploader("📄 Upload Purchase Order (PO)", type=["pdf"])

with col2:
    oa_file = st.file_uploader("📄 Upload Order Acknowledgement (OA)", type=["pdf"])

st.divider()

# 🔍 COMPARE BUTTON
if st.button("🔍 Compare Documents", use_container_width=True):

    if not po_file or not oa_file:
        st.warning("⚠️ Please upload both PDFs.")
        st.stop()

    # Extract first page
    with st.spinner("📖 Reading first page..."):
        po_text = extract_first_page(po_file)
        oa_text = extract_first_page(oa_file)

    if not po_text or not oa_text:
        st.error("❌ Could not extract text (PDF may be scanned)")
        st.stop()

    # AI compare
    with st.spinner("🤖 Comparing using AI..."):
        result = compare_with_ai(po_text, oa_text) 

    if not result:
        st.error("❌ Comparison failed")
        st.stop()

    st.divider()
    st.markdown(result)
  
