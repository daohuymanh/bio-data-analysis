# edengue_import.py
import pandas as pd
import re
import unicodedata
import os
from typing import List, Optional

def remove_diacritics_upper(s):
    """Remove diacritics and return uppercase ASCII-like string."""
    if pd.isna(s):
        return s
    s = str(s).strip()
    s_norm = unicodedata.normalize("NFKD", s)
    s_ascii = ''.join(ch for ch in s_norm if not unicodedata.combining(ch))
    # Vietnamese D/đ -> D
    s_ascii = s_ascii.replace('Đ','D').replace('đ','d')
    s_ascii = re.sub(r'\s+', ' ', s_ascii).strip().upper()
    return s_ascii

def extract_tc_rows_from_sheet(df: pd.DataFrame, month_val: int,
                               prov_name: str,
                               col_indices_map=(3,4,5,6,7),
                               bad_keywords: Optional[List[str]] = None):
    """
    df: DataFrame loaded with header=None (so columns are positional)
    month_val: numeric month to assign
    col_indices_map: 0-based indices for D,E,F,G,H -> default (3,4,5,6,7)
    returns list of dict rows
    """
    if bad_keywords is None:
        bad_keywords = ["Địa", "SỞ", "BÁO", "Ghi chú", "TOÀN TỈNH", "Nơi nhận", "Viện", "Ngày", "TC"]
    rows = []
    # find rows where any cell equals "TC" (case-insensitive, trimmed)
    tc_mask = df.apply(lambda r: r.astype(str).str.strip().str.upper().eq("TC").any(), axis=1)
    tc_indices = list(df[tc_mask].index)
    for idx in tc_indices:
        # find district: search upward in column 0, then column 1 as fallback
        district = None
        maxcol = df.shape[1]
        for i in range(idx-1, -1, -1):
            if maxcol == 0:
                break
            val = df.iat[i, 0]
            if pd.isna(val): 
                continue
            s = str(val).strip()
            if s == "": 
                continue
            if any(k.upper() in s.upper() for k in bad_keywords):
                continue
            district = s
            break
        if district is None:
            for i in range(idx-1, -1, -1):
                if maxcol > 1:
                    val = df.iat[i, 1]
                    if pd.isna(val): 
                        continue
                    s = str(val).strip()
                    if s == "": 
                        continue
                    if any(k.upper() in s.upper() for k in bad_keywords):
                        continue
                    district = s
                    break
        if district is None:
            district = "UNKNOWN"

        def safe_get(r, c):
            try:
                v = df.iat[r, c]
                if pd.isna(v):
                    return 0
                if isinstance(v, str):
                    t = v.strip().replace(",", "")
                    if re.fullmatch(r'-?\d+(\.\d+)?', t):
                        n = float(t)
                        return int(n) if n.is_integer() else n
                    # non-numeric strings -> 0 (you can change if prefer None)
                    return 0
                return v
            except Exception:
                return 0

        no_den1 = safe_get(idx, col_indices_map[0])
        no_den2 = safe_get(idx, col_indices_map[1])
        no_den3 = safe_get(idx, col_indices_map[2])
        no_den4 = safe_get(idx, col_indices_map[3])
        total_test = safe_get(idx, col_indices_map[4])

        rows.append({
            "province": prov_name,
            "district": remove_diacritics_upper(district),
            "year": 2025,
            "month": month_val,
            "No.DEN1": no_den1,
            "No.DEN2": no_den2,
            "No.DEN3": no_den3,
            "No.DEN4": no_den4,
            "Total test": total_test
        })
    return rows

def process_file_to_edengue(input_path: str,
                           output_path: str,
                           prov_name: Optional[str] = None,
                           month_min: int = 1,
                           month_max: int = 12,
                           col_map=(3,4,5,6,7),
                           append_to_existing: bool = False):
    """
    Process a single GSTX Excel file and write a new EDENGUE Excel.
    - input_path: path to province GSTX (xlsx/xlsm/xls)
    - output_path: path to write output Excel
    - prov_name: province name to write in 'province' column (if None, inferred from filename)
    - month_min/month_max: inclusive month range to import (e.g. 7-10)
    - col_map: 0-based indices for D..H (default D index=3 .. H index=7)
    - append_to_existing: if True and output_path exists, append rows to it.
    """
    if prov_name is None:
        prov_name = os.path.basename(input_path).replace(".xlsx", "").replace(".xlsm", "").replace(".xls", "")
        # remove GSTX suffix if present
        prov_name = re.sub(r'\s*GSTX.*$', '', prov_name, flags=re.I).strip().upper()
    else:
        prov_name = prov_name.strip().upper()

    # try to load workbook
    try:
        xls = pd.ExcelFile(input_path)
    except Exception as e:
        raise RuntimeError(f"Cannot open '{input_path}': {e}")

    all_rows = []
    for sheet in xls.sheet_names:
        # detect month number in sheet name
        m = re.search(r'(\d+)', str(sheet))
        if not m:
            continue
        month_val = int(m.group(1))
        if month_val < month_min or month_val > month_max:
            continue
        # read sheet without header to preserve positions
        df = pd.read_excel(input_path, sheet_name=sheet, header=None, dtype=object)
        rows = extract_tc_rows_from_sheet(df, month_val, prov_name, col_indices_map=col_map)
        all_rows.extend(rows)

    if not all_rows:
        print("No rows found for the given month range.")
        # still create empty file with header
        out_df = pd.DataFrame(columns=["province","district","year","month","No.DEN1","No.DEN2","No.DEN3","No.DEN4","Total test"])
        out_df.to_excel(output_path, index=False)
        return output_path

    out_df = pd.DataFrame(all_rows)
    # ensure column order
    cols = ["province","district","year","month","No.DEN1","No.DEN2","No.DEN3","No.DEN4","Total test"]
    out_df = out_df[cols]

    if append_to_existing and os.path.exists(output_path):
        existing = pd.read_excel(output_path)
        combined = pd.concat([existing, out_df], ignore_index=True, sort=False)
        combined.to_excel(output_path, index=False)
    else:
        out_df.to_excel(output_path, index=False)

    return output_path

# ---------------------------
# Example usage (change paths & parameters as needed)
# ---------------------------
if __name__ == "__main__":
    # Example: import AN GIANG months 7-10 into a new file
    input_file = "/path/to/AN GIANG GSTX 2025.xlsx"   # <- replace by your path
    output_file = "/path/to/EDENGUE_AN_GIANG_7_10.xlsx"
    # columns D..H are indices 3..7, set month range 7-10
    created = process_file_to_edengue(input_file, output_file,
                                      prov_name="AN GIANG",
                                      month_min=7, month_max=10,
                                      col_map=(3,4,5,6,7),
                                      append_to_existing=False)
    print("Saved:", created)
