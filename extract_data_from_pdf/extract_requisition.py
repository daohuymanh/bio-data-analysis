#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_requisition_v4.py
Update: keep Primary time selection using the LAST time after the Primary label
(avoid earlier unrelated times), but take End-clot using the FIRST time after its label
(as requested).
Usage:
    python3 extract_requisition_v4.py input.pdf output.xlsx
"""
import re
import sys
from pathlib import Path
import argparse
import pandas as pd

def safe_search(pattern, text, flags=0):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else ""

def normalize_time(t):
    if not t:
        return ""
    t = t.strip().replace('.', ':')
    m = re.match(r"^([0-9]{1,2}):([0-9]{2})$", t)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return t

def find_first_time_after_label(text, label_regex_list, lookahead=260):
    """Return the FIRST time (nearest to label start) in the window after the label."""
    time_pattern = r"([01]?[0-9][:\.][0-5][0-9])"
    text2 = text.replace("\r", "\n")
    for lab in label_regex_list:
        for m in re.finditer(lab, text2, re.IGNORECASE):
            window = text2[m.end():m.end()+lookahead]
            tm = re.search(time_pattern, window)
            if tm:
                return normalize_time(tm.group(1))
    return ""

def find_last_time_after_label(text, label_regex_list, lookahead=260):
    """Return the LAST time in the window after the label (prefers later times)."""
    time_pattern = r"([01]?[0-9][:\.][0-5][0-9])"
    text2 = text.replace("\r", "\n")
    for lab in label_regex_list:
        for m in re.finditer(lab, text2, re.IGNORECASE):
            window = text2[m.end():m.end()+lookahead]
            times = re.findall(time_pattern, window)
            if times:
                return normalize_time(times[-1])
    return ""

def find_value_after_label(text, labels, value_patterns, lookahead=140):
    text2 = text.replace("\r", "\n")
    for lab in labels:
        m = re.search(lab, text2, re.IGNORECASE)
        if m:
            window = text2[m.end():m.end()+lookahead]
            for vp in value_patterns:
                vm = re.search(vp, window, re.IGNORECASE)
                if vm:
                    return vm.group(1).strip()
    return ""

def extract_from_table_cells(cells):
    joined = " ".join([c for c in cells if c])
    out = {}

    # Volume
    if re.search(r"(Total\s*Whole\s*Blood|volume\s*collected|Whole\s*Blood\s*volume)", joined, re.IGNORECASE):
        m = re.search(r"([0-9]{1,4})\s*(?:mL|ml|ML)\b", joined)
        if m:
            out["Thể tích mẫu (mL)"] = m.group(1)
        else:
            m2 = re.search(r"\b([0-9]{1,4})\b", joined)
            if m2:
                out["Thể tích mẫu (mL)"] = m2.group(1)

    times = re.findall(r"([01]?\d[:\.][0-5]\d)", joined)
    times = [t.replace('.', ':') for t in times]

    # Start clot -> use last time in row
    if re.search(r"(Clotting\s*start|Blood\s*Clotting\s*start|start\s*time\s*clot)", joined, re.IGNORECASE):
        if times:
            out["Giờ bắt đầu đông máu"] = normalize_time(times[-1])

    # End clot -> use FIRST time in row (matches previous logic)
    if re.search(r"(Clotting\s*end|Blood\s*Clotting\s*end|end\s*time\s*clot|centrifug(e|ation)\s*end)", joined, re.IGNORECASE):
        if times:
            out["Giờ kết thúc đông"] = normalize_time(times[0])

    # Primary -> use last time in row
    if re.search(r"(Primary\s*Time|Primary\s*Time\s*sample|Primary\s*placed)", joined, re.IGNORECASE):
        if times:
            out["Giờ đặt tủ đông Primary"] = normalize_time(times[-1])

    if re.search(r"(Backup\s*1\s*Time|Backup\s*1\s*placed)", joined, re.IGNORECASE):
        if times:
            out["Giờ đặt tủ đông Backup1"] = normalize_time(times[-1])

    if re.search(r"(Backup\s*2\s*Time|Backup\s*2\s*placed)", joined, re.IGNORECASE):
        if times:
            out["Giờ đặt tủ đông Backup2"] = normalize_time(times[-1])

    # R&I
    if re.search(r"(Reactogenicity\s*and\s*Immunogenicity\s*Subset|Reactogenicity\s*&\s*Immunogenicity|R\s*&\s*I|R\s*and\s*I)", joined, re.IGNORECASE):
        mm = re.search(r"\b(Yes|No|Y|N|X|checked|unchecked)\b", joined, re.IGNORECASE)
        if mm:
            out["R và I Subset"] = mm.group(1)

    return out

def extract_text_pages(pdf_path):
    try:
        import pdfplumber
    except Exception:
        raise RuntimeError("Cần cài pdfplumber: pip install pdfplumber")
    pages_text = []
    pages_tables = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for p in pdf.pages:
            pages_text.append(p.extract_text() or "")
            try:
                tables = p.extract_tables()
            except Exception:
                tables = []
            pages_tables.append(tables)
    return pages_text, pages_tables

def parse_pdf(pdf_path):
    pages_text, pages_tables = extract_text_pages(pdf_path)
    rows = []
    for idx, text in enumerate(pages_text):
        row = {}
        text_clean = text.replace("\r", "\n")

        row["Mã sàng lọc"] = safe_search(r"Screen[_\s]?No\.?\s*[:\-]?\s*([0-9A-Za-z\-]+)", text_clean) or ""
        row["Requisition ID"] = safe_search(r"Requisition\s*ID\s*[:\-]?\s*([0-9A-Za-z\-]+)", text_clean) or ""
        if not row["Requisition ID"]:
            m = re.search(r"Requisition\s*ID", text_clean, re.IGNORECASE)
            if m:
                mm = re.search(r"[:\s]*([0-9A-Za-z\-_/]+)", text_clean[m.end():m.end()+120])
                if mm:
                    row["Requisition ID"] = mm.group(1)

        row["Mã ngẫu nhiên"] = safe_search(r"Randomization\s*Number\s*[:\-]?\s*([0-9A-Za-z\-]+)", text_clean) or ""
        row["Năm sinh"] = safe_search(r"Year\s*of\s*Birth\s*[:\-]?\s*([0-9]{4})", text_clean) or ""
        row["Giới tính"] = safe_search(r"Gender\s*[:\-]?\s*(Male|Female|M|F|Other)", text_clean) or ""

        row["Ngày lấy mẫu"] = safe_search(r"Collection\s*Date\s*[:\-]?\s*([0-3]?[0-9][-/][A-Za-z0-9]{2,9}[-/][0-9]{2,4})", text_clean) or ""
        row["Giờ lấy mẫu"] = find_first_time_after_label(text_clean, [r"Collection\s*Time"]) or ""

        visit = safe_search(r"Current\s*Visit\s*[:=\-]?\s*(?:Visit\s*)?([0-9]{1,2})", text_clean)
        if not visit:
            visit = safe_search(r"\bVisit\s*[:#-]?\s*([0-9]{1,2})", text_clean)
        row["Lần thăm khám"] = visit or ""

        # Defaults
        for k in ["Thể tích mẫu (mL)","Giờ bắt đầu đông máu","Giờ kết thúc đông","Giờ đặt tủ đông Primary",
                  "Giờ đặt tủ đông Backup1","Giờ đặt tủ đông Backup2","R và I Subset"]:
            row.setdefault(k, "")

        # Tables
        tables = pages_tables[idx] or []
        for table in tables:
            for r in table:
                cells = [ (c or "").strip() for c in r ]
                extracted = extract_from_table_cells(cells)
                for k,v in extracted.items():
                    if v:
                        row[k] = v

        # Fallbacks
        if not row.get("Thể tích mẫu (mL)"):
            m = re.search(r"([0-9]{1,4})\s*(?:mL|ml)\b", text_clean)
            if m:
                row["Thể tích mẫu (mL)"] = m.group(1)

        if not row.get("Giờ bắt đầu đông máu"):
            row["Giờ bắt đầu đông máu"] = find_last_time_after_label(text_clean, [r"Clotting\s*start", r"Blood\s*Clotting\s*start"]) or ""

        # IMPORTANT: use FIRST time after label for end-clot (previous, preferred logic)
        if not row.get("Giờ kết thúc đông"):
            row["Giờ kết thúc đông"] = find_first_time_after_label(text_clean, [r"Clotting\s*end", r"Blood\s*Clotting\s*end", r"Centrifug(e|ation)\s*end", r"End\s*time"]) or ""

        # Primary/Backup: prefer LAST time after label (since Primary earlier had wrong earlier time)
        if not row.get("Giờ đặt tủ đông Primary"):
            row["Giờ đặt tủ đông Primary"] = find_last_time_after_label(text_clean, [r"Primary\s*Time", r"Primary\s*Time\s*sample"]) or ""

        if not row.get("Giờ đặt tủ đông Backup1"):
            row["Giờ đặt tủ đông Backup1"] = find_last_time_after_label(text_clean, [r"Backup\s*1\s*Time", r"Backup\s*1"]) or ""

        if not row.get("Giờ đặt tủ đông Backup2"):
            row["Giờ đặt tủ đông Backup2"] = find_last_time_after_label(text_clean, [r"Backup\s*2\s*Time", r"Backup\s*2"]) or ""

        if not row.get("R và I Subset"):
            m = re.search(r"(Reactogenicity\s*and\s*Immunogenicity\s*Subset|R\s*&\s*I)[^\n\r]{0,160}\b(Yes|No|Y|N|X|checked|unchecked)\b", text_clean, re.IGNORECASE)
            if m:
                row["R và I Subset"] = m.group(2)

        # Normalize times
        for k in ["Giờ bắt đầu đông máu","Giờ kết thúc đông","Giờ đặt tủ đông Primary","Giờ đặt tủ đông Backup1","Giờ đặt tủ đông Backup2","Giờ lấy mẫu"]:
            if row.get(k):
                row[k] = normalize_time(row[k])

        rows.append(row)
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", help="input PDF path")
    parser.add_argument("out", nargs="?", default="RequisitionForms_extracted_v4.xlsx", help="output excel path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print("PDF không tồn tại:", pdf_path)
        sys.exit(1)

    rows = parse_pdf(pdf_path)
    if not rows:
        print("Không tìm thấy dữ liệu trong PDF.")
        sys.exit(1)

    df = pd.DataFrame(rows)
    cols_order = ["Requisition ID","Mã sàng lọc","Mã ngẫu nhiên","Năm sinh","Giới tính",
                  "Ngày lấy mẫu","Giờ lấy mẫu","Lần thăm khám","Thể tích mẫu (mL)",
                  "Giờ bắt đầu đông máu","Giờ kết thúc đông","Giờ đặt tủ đông Primary",
                  "Giờ đặt tủ đông Backup1","Giờ đặt tủ đông Backup2","R và I Subset"]
    cols_present = [c for c in cols_order if c in df.columns]
    other_cols = [c for c in df.columns if c not in cols_present]
    df = df[cols_present + other_cols]
    df.to_excel(args.out, index=False)
    print("Đã lưu:", args.out)

if __name__ == "__main__":
    main()
