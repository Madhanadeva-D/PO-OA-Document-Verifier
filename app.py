import streamlit as st
import pdfplumber
import re
from dataclasses import dataclass, field

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="PO ↔ OA Verifier", page_icon="🔍", layout="wide")

# ─── CSS ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ✅ FIXED ONLY THIS LINE */
html, body { font-family: 'Inter', sans-serif; }

header[data-testid="stHeader"] {
    display: none;
}
        
.main { background: #f0f4f8; }
.hero {
    background: linear-gradient(135deg, #0f2544 0%, #1e4d9b 60%, #2563eb 100%);
    border-radius: 18px; padding: 36px 40px; margin-bottom: 28px; color: white;
    box-shadow: 0 8px 32px rgba(37,99,235,.18);
}
.hero h1 { font-size: 2rem; font-weight: 800; margin: 0 0 6px 0; letter-spacing: -.02em; }
.hero p  { font-size: .98rem; opacity: .82; margin: 0; }
.upload-wrap {
    background: white; border-radius: 14px; padding: 22px 20px 18px;
    box-shadow: 0 2px 8px rgba(0,0,0,.06); margin-bottom: 8px;
}
.upload-tag {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: .78rem; font-weight: 700; color: white; background: #2563eb;
    border-radius: 20px; padding: 3px 12px; margin-bottom: 10px;
    letter-spacing: .04em; text-transform: uppercase;
}
.card { background: white; border-radius: 14px; padding: 22px 24px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.section-title { font-size: 1rem; font-weight: 700; color: #1e293b; margin: 0 0 14px 0; display: flex; align-items: center; gap: 8px; }
.field-row { display: flex; align-items: flex-start; gap: 14px; border-radius: 10px; padding: 14px 16px; margin-bottom: 8px; border-left: 4px solid #e2e8f0; background: #f8fafc; }
.field-row.ok   { border-left-color: #22c55e; background: #f0fdf4; }
.field-row.err  { border-left-color: #ef4444; background: #fff5f5; }
.field-row.warn { border-left-color: #f59e0b; background: #fffbeb; }
.field-label { font-size: .72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .06em; min-width: 138px; padding-top: 3px; flex-shrink: 0; }
.field-values { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.field-entry  { display: flex; flex-direction: column; }
.field-source { font-size: .68rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: .07em; margin-bottom: 1px; }
.field-val    { font-size: .88rem; color: #1e293b; line-height: 1.5; word-break: break-word; }
.badge { font-size: .7rem; font-weight: 700; padding: 4px 12px; border-radius: 20px; white-space: nowrap; align-self: flex-start; margin-top: 2px; flex-shrink: 0; }
.badge-ok   { background: #dcfce7; color: #15803d; }
.badge-err  { background: #fee2e2; color: #b91c1c; }
.badge-miss { background: #f1f5f9; color: #475569; }
.summary-band { border-radius: 12px; padding: 18px 24px; margin-bottom: 22px; display: flex; align-items: center; gap: 18px; }
.summary-band.pass { background: #f0fdf4; border: 2px solid #86efac; }
.summary-band.fail { background: #fff1f2; border: 2px solid #fca5a5; }
.summary-band.warn { background: #fffbeb; border: 2px solid #fcd34d; }
.s-icon { font-size: 2.4rem; }
.s-text h3 { margin: 0 0 3px; font-size: 1.1rem; font-weight: 700; color: #1e293b; }
.s-text p  { margin: 0; font-size: .87rem; color: #475569; }
.items-table { width: 100%; border-collapse: collapse; font-size: .87rem; }
.items-table th { background: #0f2544; color: white; padding: 11px 14px; text-align: left; font-weight: 600; font-size: .76rem; letter-spacing: .04em; text-transform: uppercase; }
.items-table th:not(:first-child) { border-left: 1px solid rgba(255,255,255,.1); }
.items-table td { padding: 11px 14px; color: #1e293b; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
.items-table tr:nth-child(even) td { background: #f8fafc; }
.items-table .total-row td { background: #1e3a5f !important; color: white; font-weight: 700; }
.num { text-align: right; }
.ctr { text-align: center; }
.pill { display: inline-block; background: #e0e7ff; color: #3730a3; font-size: .75rem; font-weight: 600; border-radius: 6px; padding: 2px 8px; }
</style>
""", unsafe_allow_html=True)

# ─── Data class ─────────────────────────────────────────────────────────────
@dataclass
class DocData:
    po_no: str = ""
    po_date: str = ""
    customer_name: str = ""
    delivery_address: str = ""
    billing_address: str = ""
    items: list = field(default_factory=list)
    raw_text: str = ""

# ─── Utilities ──────────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_file) -> str:
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text(x_tolerance=3, y_tolerance=3)
            if t:
                text += t + "\n"
    return text

def clean(s: str) -> str:
    return re.sub(r'\s+', ' ', (s or "")).strip()

def normalise_date(d: str) -> str:
    return re.sub(r'[/\-]', '.', (d or "").strip())

# ─── PO Parser ──────────────────────────────────────────────────────────────
# PO is two-column PDF. pdfplumber merges columns into single lines:
#  Line 0:  PURCHASE ORDER
#  Line 1:  No.114
#  Line 2:  Vendor Code : 0010001109   Danapur Village, Hobli Mariyammanahalli,
#  Line 3:  Name : YUKEN INDIA LIMITED.   Hosapete Taluka, Vijayanagar
#  Line 4:  Address : Lakkur HobliMalur Taluk,   District-583222
#  Line 5:  Kolar,District,PBNo.5, Koppathimmanahalli   -Karnataka ( India )
#  Line 6:  Village,   Tel No: 08394264000
#  Line 8:  MALUR-563130-Karnataka-India
#  Line 9:  E-mail: bmmispat@bmm.in
#  Line 11: P.O.No.:4100014975
#  Line 13: P.O.Date:30.09.2025
#  Line 15: PAN NO : AAACY1160E   Cont.:Raju B.R,7022036309
#
# Delivery address = BUYER (right column, lines 1-9)
# Billing address  = SUPPLIER (left column lines 4-8)
# Customer name    = Cont. field

def parse_po(text: str) -> DocData:
    d = DocData(raw_text=text)
    lines = text.splitlines()

    # P.O. No & Date
    m = re.search(r'P\.O\.No\.\s*[:\-]?\s*(\d+)', text)
    d.po_no = m.group(1).strip() if m else ""
    m = re.search(r'P\.O\.Date\s*[:\-]?\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})', text)
    d.po_date = normalise_date(m.group(1)) if m else ""

    # Customer Name: contact person at buyer side
    m = re.search(r'Cont\.\s*[:\-]\s*([^,\n]+)', text)
    d.customer_name = clean(m.group(1)) if m else ""

    # Delivery Address: extract right-column substrings from lines 1-9
    # Right column contains buyer address: No.114, Danapur Village..., Hosapete Taluka..., etc.
    delivery_parts = ["No.114"]  # line 1 is always the buyer's No.114

    # Line 2: "Vendor Code : XXXXXXXX  Danapur Village, Hobli Mariyammanahalli,"
    # Extract everything AFTER the left-col part (Vendor Code : ...)
    for l in lines:
        # Extract right-col content: after "Vendor Code : \d+" pattern
        m2 = re.search(r'Vendor Code\s*:\s*\d+\s+(.*)', l)
        if m2 and m2.group(1).strip():
            delivery_parts.append(m2.group(1).strip()); continue
        # "Name : YUKEN INDIA LIMITED.  Hosapete Taluka, Vijayanagar"
        m2 = re.search(r'Name\s*:\s*[A-Z\s\.]+\s{2,}(.*)', l)
        if m2 and m2.group(1).strip():
            delivery_parts.append(m2.group(1).strip()); continue
        # "Address : Lakkur HobliMalur Taluk,  District-583222"
        m2 = re.search(r'Address\s*:.+?\s{2,}(District-\d+.*)', l)
        if m2 and m2.group(1).strip():
            delivery_parts.append(m2.group(1).strip()); continue
        # "Kolar,District,PBNo.5,...  -Karnataka ( India )"
        m2 = re.search(r'Kolar,.+\s{2,}(-Karnataka.*)', l)
        if m2 and m2.group(1).strip():
            delivery_parts.append(m2.group(1).strip()); continue
        # "Village,  Tel No: 08394264000"
        m2 = re.search(r'^Village,\s+(Tel No:.*)', l.strip())
        if m2:
            delivery_parts.append(m2.group(1).strip()); continue
        # Standalone lines
        if re.match(r'^Fax No:', l.strip()):
            delivery_parts.append(l.strip()); continue
        if re.match(r'^E-mail:\s*bmmispat', l.strip(), re.I):
            delivery_parts.append(l.strip()); continue

    d.delivery_address = clean(' '.join(delivery_parts))

    # Billing Address: supplier left-column (lines 4-8)
    billing_parts = []
    for l in lines:
        m2 = re.search(r'Address\s*:\s*(Lakkur[^\s].*?)(?:\s{2,}|$)', l)
        if m2: billing_parts.append(m2.group(1).strip()); continue
        if re.match(r'^Kolar,District,PBNo\.5', l.strip()):
            # strip right-col: "-Karnataka ( India )"
            part = re.sub(r'\s{2,}.*$', '', l.strip())
            billing_parts.append(part); continue
        if re.match(r'^Village,$', l.strip()):
            billing_parts.append('Village,'); continue
        if re.match(r'^MALUR-\d+-Karnataka-India$', l.strip()):
            billing_parts.append(l.strip()); continue

    d.billing_address = clean(' '.join(billing_parts))

    d.items = _po_items(text)
    return d


def _po_items(text: str) -> list:
    """
    PO item row: "1  2100033529  NOS  2.000  240000.000  480000.00  566400.00  28.02.2026"
    Next line: "CTRL VLV,ELDFHG 06 EH 500 3C40 XY X D-10  INR"
    """
    items = []
    pat = re.compile(
        r'(\d+)\s+(\d{7,})\s+NOS\s+([\d.]+)\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)\s+(\d{2}\.\d{2}\.\d{4})'
    )
    gst_m = re.search(r'CGST\s*@\s*([\d.]+)%.*?SGST\s*@\s*([\d.]+)%', text)
    gst_str = f"CGST {gst_m.group(1)}% + SGST {gst_m.group(2)}%" if gst_m else ""

    for m in pat.finditer(text):
        pos = m.end()
        rest = text[pos:pos+200].strip().splitlines()
        desc = clean(rest[0]) if rest else ""
        desc = re.sub(r'\s*INR\s*$', '', desc).strip()
        items.append({
            'sno': m.group(1), 'description': desc,
            'item_code': m.group(2), 'qty': m.group(3),
            'rate': m.group(4).replace(',', ''),
            'base_value': m.group(5).replace(',', ''),
            'total_value': m.group(6).replace(',', ''),
            'delivery_date': m.group(7), 'gst': gst_str,
        })
    return items


# ─── OA Parser ──────────────────────────────────────────────────────────────
# OA text (spaces collapsed by PDF font):
#  Line  4: To: OrderAcknowledgement
#  Line  5: BMMIspatLimited   No : 332650569       ← To: block, strip right col
#  Line  6: Taluk,#114DanapurVillage,Hospetbellary   Date : 08.10.2025
#  Line  7: bellaryDistrict,HOSPET583222   Chargeable
#  Line  8: India
#  Line  9: ClientCode : 4B75                       ← skip this
#  Line 10: A/cTo:
#  Line 11: YourP.ONo : 4100014975                  ← skip
#  Line 12: BMMIspatLimited                         ← billing name
#  Line 13: YourP.ODate : 30.09.2025                ← skip
#  Line 14: Taluk, #114DanapurVillage,Hospet         ← billing addr
#  Line 15: YourGSTNo : 29AACCB3556B1ZY             ← skip
#  Line 16: bellaryDistrict,HOSPET                   ← billing addr
#  Line 17: Ref No :                                 ← skip
#  Line 18: India-583222                             ← billing addr
#  Line 19: ContactPerson :                          ← skip
#  Line 20: Transporter : YIL                        ← skip
#  Line 21: DespatchType :DIRECT                     ← end of billing

def parse_oa(text: str) -> DocData:
    d = DocData(raw_text=text)
    lines = text.splitlines()

    # P.O. No & Date
    m = re.search(r'YourP\.ONo\s*:\s*(\d+)', text, re.I)
    d.po_no = m.group(1).strip() if m else ""
    m = re.search(r'YourP\.ODate\s*:\s*(\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4})', text, re.I)
    d.po_date = normalise_date(m.group(1)) if m else ""

    to_idx   = next((i for i,l in enumerate(lines) if re.match(r'To\s*:', l.strip(), re.I)), None)
    ac_idx   = next((i for i,l in enumerate(lines) if re.match(r'A/c\s*To\s*:|A/cTo\s*:', l.strip(), re.I)), None)
    desp_idx = next((i for i,l in enumerate(lines) if re.match(r'Despatch', l.strip(), re.I)), None)

    # Right-col noise pattern in "To:" block
    right_noise = re.compile(
        r'\s+(No\s*:|Date\s*:|Chargeable|OrderAcknowledgement)',
        re.I
    )
    # Lines to skip in To: block entirely
    skip_to = re.compile(r'^(ClientCode|YourP\.|Ref\s*No|ContactPerson|Transporter)', re.I)

    if to_idx is not None:
        end = ac_idx if (ac_idx and ac_idx > to_idx) else to_idx + 6
        to_lines = []
        for l in lines[to_idx+1:end]:
            l = l.strip()
            if not l or skip_to.search(l): continue
            # strip right-column noise (e.g. "No : 332650569", "Date : ...")
            l = right_noise.split(l)[0].strip()
            if l:
                to_lines.append(l)
        if to_lines:
            d.customer_name = to_lines[0]
            d.delivery_address = clean(' '.join(to_lines))

    # A/c To block: skip YourP., YourGST, Ref No, ContactPerson, Transporter
    skip_ac = re.compile(r'^(YourP\.|YourGST|Ref\s*No|ContactPerson|Transporter)', re.I)
    if ac_idx is not None:
        end2 = desp_idx if (desp_idx and desp_idx > ac_idx) else ac_idx + 10
        ac_lines = []
        for l in lines[ac_idx+1:end2]:
            l = l.strip()
            if not l or skip_ac.search(l): continue
            # strip right-col noise
            l = right_noise.split(l)[0].strip()
            if l:
                ac_lines.append(l)
        if ac_lines:
            d.billing_address = clean(' '.join(ac_lines))

    d.items = _oa_items(text)
    return d


def _oa_items(text: str) -> list:
    """
    OA item row: "1 ELDFHG-06-500-3C40-XY-20 07.04.2026 2.000 240,000.00 0.00 0.000 9.00 9.00 0.00 566,400.00"
    """
    items = []
    pat = re.compile(
        r'(\d)\s+(ELDFHG[\w\-]+)\s+(\d{2}\.\d{2}\.\d{4})\s+([\d.]+)\s+([\d,]+\.\d{2})\s+'
        r'[\d.]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d,]+\.\d{2})'
    )
    for m in pat.finditer(text):
        cgst = float(m.group(6))
        sgst = float(m.group(7))
        gst_str = f"CGST {cgst:.0f}% + SGST {sgst:.0f}%"
        pos = m.end()
        rest = text[pos:pos+30].strip()
        ic_m = re.match(r'(\d{7,})', rest)
        items.append({
            'sno': m.group(1), 'description': m.group(2),
            'item_code': ic_m.group(1)[:10] if ic_m else "",
            'qty': m.group(4),
            'rate': m.group(5).replace(',', ''),
            'base_value': '',
            'total_value': m.group(9).replace(',', ''),
            'delivery_date': m.group(3), 'gst': gst_str,
        })
    return items


# ─── Compare ────────────────────────────────────────────────────────────────
def word_overlap(a: str, b: str) -> float:
    a_w = set(re.findall(r'\w{3,}', a.lower()))
    b_w = set(re.findall(r'\w{3,}', b.lower()))
    if not a_w or not b_w: return 0.0
    return len(a_w & b_w) / max(len(a_w), len(b_w))

def compare_docs(po: DocData, oa: DocData) -> list:
    def add(label, pv, ov, mode='exact'):
        if not pv and not ov: status = 'missing'
        elif not pv or not ov: status = 'missing'
        elif mode == 'exact': status = 'ok' if pv.strip() == ov.strip() else 'mismatch'
        else: status = 'ok' if word_overlap(pv, ov) >= 0.35 else 'mismatch'
        return {'label': label, 'po_val': pv, 'oa_val': ov, 'status': status}

    return [
        add('P.O. Number',      po.po_no,           oa.po_no),
        add('P.O. Date',        po.po_date,          oa.po_date),
        add('Customer Name',    po.customer_name,    oa.customer_name,    'fuzzy'),
        add('Delivery Address', po.delivery_address, oa.delivery_address, 'fuzzy'),
        add('Billing Address',  po.billing_address,  oa.billing_address,  'fuzzy'),
    ]


# ─── Render ─────────────────────────────────────────────────────────────────
def render_field(c: dict):
    badges = {'ok': ('badge-ok','✓ Match'), 'mismatch': ('badge-err','✗ Mismatch'), 'missing': ('badge-miss','— Missing')}
    rows   = {'ok': 'ok', 'mismatch': 'err', 'missing': 'warn'}
    bcls, btxt = badges[c['status']]
    pv = c['po_val'] or '<span style="color:#94a3b8;font-style:italic">Not extracted</span>'
    ov = c['oa_val'] or '<span style="color:#94a3b8;font-style:italic">Not extracted</span>'
    st.markdown(f"""
    <div class="field-row {rows[c['status']]}">
        <div class="field-label">{c['label']}</div>
        <div class="field-values">
            <div class="field-entry">
                <span class="field-source">Purchase Order</span>
                <span class="field-val">{pv}</span>
            </div>
            <div class="field-entry">
                <span class="field-source">Order Acknowledgement</span>
                <span class="field-val">{ov}</span>
            </div>
        </div>
        <span class="badge {bcls}">{btxt}</span>
    </div>""", unsafe_allow_html=True)


def render_items(po_items: list, oa_items: list):
    primary = po_items if po_items else oa_items
    if not primary:
        st.info("No line items could be extracted automatically.")
        return

    oa_map = {it['sno']: it for it in oa_items}
    rows_html = ""
    total_base = total_val = 0.0

    for it in primary:
        oa_it = oa_map.get(it['sno'], {})
        try: bv = float(it.get('base_value') or 0)
        except: bv = 0.0
        try: tv = float(it.get('total_value') or oa_it.get('total_value') or 0)
        except: tv = 0.0
        try: rate = float((it.get('rate') or '0').replace(',',''))
        except: rate = 0.0
        try: qty = float(it.get('qty') or 0)
        except: qty = 0.0
        if bv == 0 and rate and qty: bv = rate * qty
        total_base += bv
        total_val  += tv
        gst   = it.get('gst') or oa_it.get('gst') or ""
        desc  = it.get('description','')
        ic    = it.get('item_code','') or oa_it.get('item_code','')
        ddate = it.get('delivery_date','') or oa_it.get('delivery_date','')

        rows_html += f"""<tr>
            <td class="ctr">{it['sno']}</td>
            <td>{desc}{f'<br><small style="color:#94a3b8">Code: {ic}</small>' if ic else ''}</td>
            <td class="ctr">{qty:.3f}</td>
            <td class="num">&#8377;{rate:,.2f}</td>
            <td class="num">&#8377;{bv:,.2f}</td>
            <td class="ctr"><span class="pill">{gst}</span></td>
            <td class="num">&#8377;{tv:,.2f}</td>
            <td class="ctr">{ddate}</td>
        </tr>"""

    rows_html += f"""<tr class="total-row">
        <td colspan="4">TOTAL</td>
        <td class="num">&#8377;{total_base:,.2f}</td>
        <td></td>
        <td class="num">&#8377;{total_val:,.2f}</td>
        <td></td>
    </tr>"""

    st.markdown(f"""<table class="items-table">
        <thead><tr>
            <th class="ctr">S.No</th>
            <th>Description</th>
            <th class="ctr">Qty</th>
            <th class="num">Rate / Unit</th>
            <th class="num">Base Value</th>
            <th class="ctr">GST</th>
            <th class="num">Total Value</th>
            <th class="ctr">Delivery Date</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)


# ─── App ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>🔍 PO ↔ OA Document Verifier</h1>
    <p>Upload a Purchase Order and an Order Acknowledgement to automatically verify key fields, detect mismatches, and review line items.</p>
</div>""", unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown('<div class="upload-wrap"><div class="upload-tag">📄 Purchase Order</div>', unsafe_allow_html=True)
    po_file = st.file_uploader("Upload PO PDF", type="pdf", key="po", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="upload-wrap"><div class="upload-tag">📋 Order Acknowledgement</div>', unsafe_allow_html=True)
    oa_file = st.file_uploader("Upload OA PDF", type="pdf", key="oa", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

if po_file and oa_file:
    with st.spinner("Parsing documents…"):
        po_text = extract_text_from_pdf(po_file)
        oa_text = extract_text_from_pdf(oa_file)
        po_data = parse_po(po_text)
        oa_data = parse_oa(oa_text)
        comparisons = compare_docs(po_data, oa_data)

    n_ok = sum(1 for c in comparisons if c['status'] == 'ok')
    n_mm = sum(1 for c in comparisons if c['status'] == 'mismatch')
    n_ms = sum(1 for c in comparisons if c['status'] == 'missing')

    if n_mm == 0 and n_ms == 0:
        st.markdown(f"""<div class="summary-band pass"><div class="s-icon">✅</div>
            <div class="s-text"><h3>All Fields Match</h3>
            <p>PO and OA are fully consistent across all {n_ok} checked fields.</p></div></div>""",
            unsafe_allow_html=True)
    elif n_mm > 0:
        st.markdown(f"""<div class="summary-band fail"><div class="s-icon">❌</div>
            <div class="s-text"><h3>{n_mm} Mismatch{'es' if n_mm>1 else ''} Detected</h3>
            <p>{n_ok} match &nbsp;·&nbsp; {n_mm} mismatch{'es' if n_mm>1 else ''} &nbsp;·&nbsp; {n_ms} not extracted</p></div></div>""",
            unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="summary-band warn"><div class="s-icon">⚠️</div>
            <div class="s-text"><h3>{n_ms} Field{'s' if n_ms>1 else ''} Could Not Be Read</h3>
            <p>{n_ok} match &nbsp;·&nbsp; {n_ms} extraction issue{'s' if n_ms>1 else ''}</p></div></div>""",
            unsafe_allow_html=True)

    # Field comparison
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔎 Field-by-Field Comparison</div>', unsafe_allow_html=True)
    for c in comparisons:
        render_field(c)
    st.markdown('</div>', unsafe_allow_html=True)

    # Line items
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📦 Line Items</div>', unsafe_allow_html=True)
    render_items(po_data.items, oa_data.items)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    st.markdown("""
    <div style="text-align:center;padding:70px 20px;color:#94a3b8;">
        <div style="font-size:3.5rem;margin-bottom:16px">📂</div>
        <div style="font-size:1.15rem;font-weight:700;color:#475569;margin-bottom:6px">
            Upload both PDFs above to begin verification
        </div>
        <div style="font-size:.9rem">
            Supports Purchase Orders (BMM format) and Order Acknowledgements (Yuken format)
        </div>
    </div>""", unsafe_allow_html=True)