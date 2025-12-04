import streamlit as st
import pandas as pd

st.title("Farfetch SKU Lookup (SKU → Product ID)")

# -----------------------
# Upload files
# -----------------------
assort_file = st.file_uploader("Upload Assortment File (CSV/XLSX)", type=["csv","xlsx"])
stock_files = st.file_uploader("Upload Farfetch Export Files (multiple)", type=["csv","xlsx"], accept_multiple_files=True)

if not assort_file or not stock_files:
    st.stop()

# -----------------------
# Load assortment
# -----------------------
if assort_file.name.endswith(".csv"):
    df_assort = pd.read_csv(assort_file)
else:
    df_assort = pd.read_excel(assort_file)

# normalize headers
df_assort.columns = df_assort.columns.str.strip()

if "SKU" not in df_assort.columns:
    st.error("Assortment file must have column 'SKU'")
    st.stop()

df_assort["SKU"] = df_assort["SKU"].astype(str).str.strip().str.upper()

# -----------------------
# Load stock files
# -----------------------
stock_points = {}
for f in stock_files:
    fname = f.name.lower()
    if f.name.endswith(".csv"):
        df_stock = pd.read_csv(f)
    else:
        df_stock = pd.read_excel(f)
    
    df_stock.columns = df_stock.columns.str.strip()

    required_cols = ["Product ID", "Partner barcode"]
    missing_cols = [c for c in required_cols if c not in df_stock.columns]
    if missing_cols:
        st.error(f"File {f.name} missing required columns: {missing_cols}")
        st.stop()

    df_stock["Partner barcode"] = df_stock["Partner barcode"].astype(str).str.strip().str.upper()
    df_stock["Product ID"] = df_stock["Product ID"].astype(str).str.strip()

    # detect stock point from filename
    sp = None
    for code in ["HK","US","DE","CH","JP","AU"]:
        if code.lower() in fname:
            sp = code
            break
    if not sp:
        st.warning(f"Could not detect GEO from filename {f.name}")
        continue

    stock_points[sp] = df_stock

# -----------------------
# Lookup SKUs
# -----------------------
result = df_assort.copy()

for sp, df in stock_points.items():
    ff_ids = []
    # make lookup dict
    lookup = dict(zip(df["Partner barcode"], df["Product ID"]))
    for sku in result["SKU"]:
        ff_ids.append(lookup.get(sku, ""))
    result[f"{sp} FF ID"] = ff_ids

st.success("SKU lookup complete!")
st.dataframe(result)

# -----------------------
# Download
# -----------------------
csv = result.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download CSV",
    data=csv,
    file_name="sku_lookup_results.csv",
    mime="text/csv"
)
