#!/usr/bin/env python3
"""
convert_excel_nodiacritics.py

Usage:
    python convert_excel_nodiacritics.py input.xlsx output.csv
    python convert_excel_nodiacritics.py input.xlsm --sheet "Sheet1" out.csv
    python convert_excel_nodiacritics.py input.xlsx --all-sheets out_dir/

This script:
 - Reads an Excel file (first sheet by default)
 - Removes diacritics (Vietnamese accents) from headers and string cells
 - Replaces spaces in headers with underscores and makes headers UPPERCASE
 - Saves output as CSV (UTF-8) or multiple CSVs if --all-sheets
"""

import argparse
import pandas as pd
import unicodedata
import re
import os
import sys

def remove_diacritics(text):
    """Remove diacritics from a string, preserving ASCII characters."""
    if pd.isna(text):
        return text
    s = str(text)
    nk = unicodedata.normalize("NFKD", s)
    return "".join([c for c in nk if not unicodedata.combining(c)])

def sanitize_header(col):
    """Convert header to ascii no-diacritics, replace whitespace with underscore, uppercase."""
    s = "" if col is None else str(col)
    s = remove_diacritics(s)
    s = re.sub(r"\s+", "_", s.strip())         # spaces -> underscore
    s = re.sub(r"[^A-Za-z0-9_]", "", s)        # remove other punctuation (optional)
    if s == "":
        s = "COL"
    return s.upper()

def process_dataframe(df):
    """Remove diacritics in all string/object columns of df."""
    # Process headers
    new_cols = [sanitize_header(c) for c in df.columns]
    # Ensure uniqueness of headers
    seen = {}
    uniq_cols = []
    for c in new_cols:
        base = c
        i = 1
        while c in seen:
            c = f"{base}_{i}"
            i += 1
        seen[c] = True
        uniq_cols.append(c)
    df.columns = uniq_cols

    # Convert string/object columns: remove diacritics from strings
    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            # apply remove_diacritics only for actual strings; keep NaN and numbers as-is
            df[col] = df[col].apply(lambda x: remove_diacritics(x) if isinstance(x, str) else x)
    return df

def read_and_process_single_sheet(input_path, sheet_name=None):
    """Read an Excel sheet into a dataframe and process it."""
    if sheet_name:
        df = pd.read_excel(input_path, sheet_name=sheet_name, dtype=object)
    else:
        df = pd.read_excel(input_path, dtype=object)  # first sheet by default
    df = process_dataframe(df)
    return df

def main():
    p = argparse.ArgumentParser(description="Convert Excel -> CSV with no diacritics and R-friendly headers.")
    p.add_argument("input", help="Input Excel file (.xlsx or .xlsm)")
    p.add_argument("output", help="Output CSV file path OR output directory if --all-sheets used")
    p.add_argument("--sheet", "-s", help="Sheet name to convert (default: first sheet)")
    p.add_argument("--all-sheets", "-a", action="store_true", help="Export every sheet to separate CSVs inside output directory")
    p.add_argument("--no-header", action="store_true", help="If sheet has no header row; then output columns as COL1, COL2, ... (still remove diacritics in cell strings)")
    args = p.parse_args()

    input_path = args.input
    output_path = args.output

    if not os.path.exists(input_path):
        print("ERROR: input file not found:", input_path, file=sys.stderr)
        sys.exit(2)

    # Handle all sheets mode
    if args.all_sheets:
        # output_path must be a directory
        if not os.path.exists(output_path):
            os.makedirs(output_path, exist_ok=True)
        xls = pd.ExcelFile(input_path)
        for sheet in xls.sheet_names:
            print("Processing sheet:", sheet)
            try:
                df = pd.read_excel(input_path, sheet_name=sheet, dtype=object)
            except Exception as e:
                print(f"  Skipping sheet {sheet} due to read error: {e}", file=sys.stderr)
                continue
            # If no header option: create generic headers
            if args.no_header:
                df.columns = [f"COL{i+1}" for i in range(len(df.columns))]
            df = process_dataframe(df)
            # sanitize sheet name for filename
            safe_sheet = re.sub(r"[^0-9A-Za-z_]", "_", remove_diacritics(sheet))[:40]
            out_file = os.path.join(output_path, f"{safe_sheet}.csv")
            df.to_csv(out_file, index=False, encoding="utf-8")
            print("  Saved:", out_file)
        print("All sheets processed.")
        return

    # Single sheet mode
    df = read_and_process_single_sheet(input_path, sheet_name=args.sheet)
    # Save CSV
    # If output directory given, try to create it
    d = os.path.dirname(output_path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    print("Saved:", output_path)

if __name__ == "__main__":
    main()
