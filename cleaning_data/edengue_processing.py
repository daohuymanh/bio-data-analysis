
"""
EDENGUE processing script
Reproduces the aggregation logic used in the assistant conversation.

Usage (example):
    python edengue_processing.py --src /path/to/Mau_nhan_2021.xlsx --out /path/to/EDENGUE_2021_filled.xlsx --year 2021 --province_idx 13 --district_idx 12 --month_idx 21 --du_idx 124 --mode single_du

Or use named columns:
    python edengue_processing.py --src Mau_nhan_2019.xlsx --out EDENGUE_2019_filled.xlsx --year 2019 --province_col "TỈNH" --month_col "NGÀY\n KHỞI BỆNH" --ap_col "Unnamed: 41" --bb_col "Unnamed: 53" --du_col "Unnamed: 124"

Modes:
 - single_du: count DEN1..4 and Total test from a single result column (du_col)
 - two_cols: use two columns (e.g., DU and AP) to detect DEN types (used for some years)
 - three_cols: use three columns (AP, BB, DU) to detect DEN types (used for 2019)
 - three_cols_three_sources: general name for three-columns aggregate detection

Notes:
 - Province and district will be normalized by removing Vietnamese marks and uppercased.
 - Month will be extracted by parsing the specified month/date column to datetime and taking .month.
 - Total test is counted as number of records that have at least one non-empty value among the result columns.
"""

import argparse
import pandas as pd
import unicodedata
import sys

def normalize(text):
    if pd.isna(text):
        return None
    s = str(text)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.upper().strip()

def col_by_index_or_name(df, idx_or_name):
    # If integer-like, return by index; otherwise, try exact column name
    if idx_or_name is None:
        return None
    try:
        # allow integer inputs as strings too
        if isinstance(idx_or_name, int) or (isinstance(idx_or_name, str) and idx_or_name.isdigit()):
            idx = int(idx_or_name)
            if idx < len(df.columns):
                return df.columns[idx]
            return None
    except Exception:
        pass
    # fallback to name matching
    if isinstance(idx_or_name, str):
        # exact match first
        for c in df.columns:
            if str(c) == idx_or_name:
                return c
        # case-insensitive contains match
        u = idx_or_name.upper()
        for c in df.columns:
            if u in str(c).upper():
                return c
    return None

def detect_den_from_cols(row, cols, den_token):
    # den_token like "DEN1" or "DEN2"
    for c in cols:
        if c not in row:
            continue
        val = row[c]
        if pd.isna(val):
            continue
        v = str(val).replace("-", "").upper()
        if den_token in v:
            return True
    return False

def process(
    src_path,
    out_path,
    year,
    province_idx_or_name,
    district_idx_or_name=None,
    month_idx_or_name=None,
    result_cols_idx_or_name=None,
    mode="single_du"
):
    df = pd.read_excel(src_path)
    # Resolve columns to actual names
    province_col = col_by_index_or_name(df, province_idx_or_name)
    district_col = col_by_index_or_name(df, district_idx_or_name) if district_idx_or_name is not None else None
    month_col = col_by_index_or_name(df, month_idx_or_name) if month_idx_or_name is not None else None

    # result_cols_idx_or_name can be a comma-separated list or a single value
    result_cols = []
    if result_cols_idx_or_name:
        if isinstance(result_cols_idx_or_name, (list, tuple)):
            tokens = result_cols_idx_or_name
        else:
            # split on commas
            tokens = [t.strip() for t in str(result_cols_idx_or_name).split(",") if t.strip()!='']
        for t in tokens:
            colname = col_by_index_or_name(df, t)
            if colname is None:
                raise ValueError(f"Could not find result column for token '{t}'")
            result_cols.append(colname)

    # Prepare fields
    if province_col is None:
        raise ValueError("Province column not found")
    df["province"] = df[province_col].apply(normalize)
    if district_col is not None:
        df["district"] = df[district_col].apply(normalize)
    else:
        df["district"] = None

    df["year"] = int(year)

    if month_col:
        df["month"] = pd.to_datetime(df[month_col], errors="coerce").dt.month
    else:
        df["month"] = None

    # create DEN flags
    for d in [1,2,3,4]:
        den_token = f"DEN{d}"
        if len(result_cols) == 0:
            df[f"DEN{d}"] = False
        else:
            df[f"DEN{d}"] = df.apply(lambda r: detect_den_from_cols(r, result_cols, den_token), axis=1)

    # Total test
    if len(result_cols) == 0:
        df["TOTAL_TEST"] = 0
    else:
        df["TOTAL_TEST"] = df[result_cols].notna().any(axis=1).astype(int)

    # Aggregate
    group_cols = ["province"]
    if "district" in df.columns and df["district"].notna().any():
        group_cols.append("district")
    group_cols += ["year","month"]

    agg = df.groupby(group_cols, dropna=False).agg(
        **{
            "No.DEN1": ("DEN1","sum"),
            "No.DEN2": ("DEN2","sum"),
            "No.DEN3": ("DEN3","sum"),
            "No.DEN4": ("DEN4","sum"),
            "Total test": ("TOTAL_TEST","sum")
        }
    ).reset_index()

    agg.to_excel(out_path, index=False)
    print(f"Saved aggregated file to {out_path} with {len(agg)} rows.")

def parse_args_and_run():
    parser = argparse.ArgumentParser(description='Process Mau_nhan -> EDENGUE aggregation')
    parser.add_argument('--src', required=True, help='Path to source Mau_nhan_YYYY.xlsx')
    parser.add_argument('--out', required=True, help='Output path for aggregated EDENGUE_YYYY_filled.xlsx')
    parser.add_argument('--year', required=True, type=int, help='Year integer (2019,2020,...)')
    parser.add_argument('--province_idx', help='Province column index (0-based) or name (e.g., "TỈNH" or "13")')
    parser.add_argument('--district_idx', help='District column index (0-based) or name')
    parser.add_argument('--month_idx', help='Month/date column index (0-based) or name')
    parser.add_argument('--result_cols', help='Comma-separated list of result columns (indexes or names), e.g., "124" or "41,53,124"')
    args = parser.parse_args()

    process(
        src_path=args.src,
        out_path=args.out,
        year=args.year,
        province_idx_or_name=args.province_idx,
        district_idx_or_name=args.district_idx,
        month_idx_or_name=args.month_idx,
        result_cols_idx_or_name=args.result_cols.split(",") if args.result_cols else None
    )

if __name__ == '__main__':
    # If script is run directly, parse args; otherwise functions can be imported.
    if len(sys.argv) > 1:
        parse_args_and_run()
    else:
        print("This module implements EDENGUE aggregation. Import and call process() or run with command-line arguments.")
