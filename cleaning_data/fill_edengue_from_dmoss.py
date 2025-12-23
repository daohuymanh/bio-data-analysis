#!/usr/bin/env python3
\"\"\"fill_edengue_from_dmoss.py

Usage examples:
    # Process specific DMOSS files and append to an existing EDENGUE file
    python fill_edengue_from_dmoss.py --dmoss DMOSS_2015.xlsx DMOSS_2016.xlsx --edengue EDENGUE_2015_2024.xlsx --out EDENGUE_merged.xlsx

    # Process all DMOSS_YYYY.xlsx files in current folder and append to a base EDENGUE (or create new)
    python fill_edengue_from_dmoss.py --glob "DMOSS_*.xlsx" --out EDENGUE_merged.xlsx

Behavior:
- Each DMOSS workbook is assumed to have one sheet per province (sheet name = province).
- In each sheet the expected layout (default) is:
    Row 0: header with "Tháng 1", "Tháng 2", ..., in columns 1..12
    Row 1: D1 values for months 1..12
    Row 2: D2 values
    Row 3: D3 values
    Row 4: D4 values
    Row 6: Tong values (Total test)
  If your files differ, use --rows to change the row indices (0-based).
- The script will normalize province names by removing Vietnamese diacritics and converting to UPPERCASE.
- The output file will have columns:
    province, district, year, Month, No. DEN1, No. DEN2, No. DEN3, No. DEN4, Total test
\"\"\"

import argparse
import glob
import os
import unicodedata
from pathlib import Path
from typing import List, Optional

import pandas as pd


def remove_diacritics_ascii(s: str) -> str:
    if not isinstance(s, str):
        return s
    # Replace special Đ/đ with D/d before normalization so we keep ASCII 'D'
    s = s.replace('Đ', 'D').replace('đ', 'd')
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)])


def read_dmoss_sheet(df: pd.DataFrame, d1_row: int, d2_row: int, d3_row: int,
                     d4_row: int, total_row: int, months_col_start: int = 1) -> List[dict]:
    """
    Read rows from a DMOSS sheet (pandas DataFrame) and return a list of dicts for 12 months.
    Assumes months are in columns months_col_start .. months_col_start+11
    Row indices are 0-based.
    """
    rows = []
    for i, month in enumerate(range(1, 13)):
        col_idx = months_col_start + i
        def get_cell(r):
            try:
                v = df.iat[r, col_idx]
                if pd.isna(v):
                    return None
                # Convert floats like 1.0 -> 1 (int)
                if isinstance(v, float) and v.is_integer():
                    return int(v)
                return v
            except Exception:
                return None

        rows.append({
            'Month': month,
            'No. DEN1': get_cell(d1_row),
            'No. DEN2': get_cell(d2_row),
            'No. DEN3': get_cell(d3_row),
            'No. DEN4': get_cell(d4_row),
            'Total test': get_cell(total_row)
        })
    return rows


def process_dmoss_file(dmoss_path: Path, year: Optional[int] = None,
                       d1_row: int = 1, d2_row: int = 2, d3_row: int = 3,
                       d4_row: int = 4, total_row: int = 6, months_col_start: int = 1) -> pd.DataFrame:
    """
    Process one DMOSS workbook and return a DataFrame ready to append to EDENGUE.
    """
    xls = pd.ExcelFile(dmoss_path)
    all_rows = []
    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(dmoss_path, sheet_name=sheet_name, header=None)
        except Exception as e:
            print(f\"Warning: could not read sheet {sheet_name} in {dmoss_path}: {e}\")
            continue
        province_raw = sheet_name
        province = remove_diacritics_ascii(province_raw).upper()
        monthly = read_dmoss_sheet(df, d1_row, d2_row, d3_row, d4_row, total_row, months_col_start)
        for m in monthly:
            row = {
                'province': province,
                'district': '',
                'year': year if year is not None else infer_year_from_filename(dmoss_path.name),
                'Month': m['Month'],
                'No. DEN1': m['No. DEN1'],
                'No. DEN2': m['No. DEN2'],
                'No. DEN3': m['No. DEN3'],
                'No. DEN4': m['No. DEN4'],
                'Total test': m['Total test']
            }
            all_rows.append(row)
    df_out = pd.DataFrame(all_rows, columns=['province', 'district', 'year', 'Month',
                                             'No. DEN1', 'No. DEN2', 'No. DEN3', 'No. DEN4', 'Total test'])
    return df_out


def infer_year_from_filename(name: str) -> Optional[int]:
    # Try to extract a 4-digit year from filename like DMOSS_2015.xlsx
    import re
    m = re.search(r'(20\d{2})', name)
    if m:
        try:
            return int(m.group(1))
        except:
            return None
    return None


def load_base_edengue(edengue_path: Optional[Path]) -> pd.DataFrame:
    # If edengue_path provided and exists, load it; otherwise return empty dataframe with correct columns
    cols = ['province', 'district', 'year', 'Month', 'No. DEN1', 'No. DEN2', 'No. DEN3', 'No. DEN4', 'Total test']
    if edengue_path is None:
        return pd.DataFrame(columns=cols)
    if edengue_path.exists():
        return pd.read_excel(edengue_path, dtype=object)
    return pd.DataFrame(columns=cols)


def main(dmoss_files: List[str], edengue_file: Optional[str], out_file: str,
         d1_row: int, d2_row: int, d3_row: int, d4_row: int, total_row: int, months_col_start: int):
    ed_base = load_base_edengue(Path(edengue_file) if edengue_file else None)
    appended = []
    for f in dmoss_files:
        p = Path(f)
        if not p.exists():
            print(f\"File not found: {f} (skipping)\")
            continue
        year = infer_year_from_filename(p.name)
        df_year = process_dmoss_file(p, year=year,
                                     d1_row=d1_row, d2_row=d2_row, d3_row=d3_row, d4_row=d4_row,
                                     total_row=total_row, months_col_start=months_col_start)
        appended.append(df_year)

    if appended:
        df_app = pd.concat(appended, ignore_index=True)
        # Ensure column order and types are consistent with base
        final = pd.concat([ed_base, df_app], ignore_index=True, sort=False)
    else:
        final = ed_base

    # Save to Excel
    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.to_excel(out_path, index=False)
    print(f\"Saved merged EDENGUE to: {out_path.resolve()}\")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Merge DMOSS year files into EDENGUE format')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dmoss', nargs='+', help='List of DMOSS Excel file paths to process')
    group.add_argument('--glob', help='Glob pattern to find DMOSS files, e.g. \"DMOSS_*.xlsx\"')

    parser.add_argument('--edengue', help='Existing EDENGUE file to append to (optional)', default=None)
    parser.add_argument('--out', help='Output Excel file to save (required)', required=True)
    parser.add_argument('--d1-row', type=int, default=1, help='0-based row index for D1 (default 1)')
    parser.add_argument('--d2-row', type=int, default=2, help='0-based row index for D2 (default 2)')
    parser.add_argument('--d3-row', type=int, default=3, help='0-based row index for D3 (default 3)')
    parser.add_argument('--d4-row', type=int, default=4, help='0-based row index for D4 (default 4)')
    parser.add_argument('--total-row', type=int, default=6, help='0-based row index for Tong/Total (default 6)')
    parser.add_argument('--months-col-start', type=int, default=1, help='0-based start column for Month1 (default 1)')

    args = parser.parse_args()
    if args.dmoss:
        files = args.dmoss
    else:
        files = sorted(glob.glob(args.glob))

    main(files, args.edengue, args.out,
         d1_row=args.d1_row, d2_row=args.d2_row, d3_row=args.d3_row, d4_row=args.d4_row,
         total_row=args.total_row, months_col_start=args.months_col_start)
