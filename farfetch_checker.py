import streamlit as st
import pandas as pd

st.set_page_config(page_title="Farfetch SKU Checker", layout="wide")
st.title("Farfetch SKU Checker — Ordered Checks (SKU → Netta → Optional)")

st.markdown("""
### Required Column Headers (no trailing spaces)

**Assortment file:**
- `SKU`
- `Netta product ID`
- `Optional product ID`

**Farfetch stock exports:**
- `Product ID`
- `Partner product ID`
- `Partner barcode`
""")

# ------------------------------------------------------------
# Normalization helpers
# ------------------------------------------------------------
def normalize_value(v):
    if pd.isna(v):
        return ""
    return str(v).strip().upper()

def normalize_series(col):
    return col.fillna("").astype(str).str.strip().str.upper()

# ------------------------------------------------------------
# Upload assortment
# ------------------------------------------------------------
assortment_file = st.file_uploader("Upload Assortment CSV/XLSX", type=["csv", "xlsx"])

if not assortment_file:
    st.stop()

# Load assortment
try:
    if assortment_file.name.lower().endswith(".xlsx"):
        assort = pd.read_excel(assortment_file, dtype=str)
    else:
        assort = pd.read_csv(assortment_file, dtype=str)
except Exception as e:
    st.error(f"Error reading assortment file: {e}")
    st.stop()

required_cols = ["SKU", "Netta product ID", "Optional product ID"]
missing = [c for c in required_cols if c not in assort.columns]
if missing:
    st.error(f"Assortment file is missing required columns: {missing}")
    st.stop()

# Normalize values
assort["SKU"] = normalize_series(assort["SKU"])
assort["Netta product ID"] = normalize_series(assort["Netta product ID"])
assort["Optional product ID"] = normalize_series(assort["Optional product ID"])

st.subheader("Assortment preview")
st.dataframe(assort.head(10))

# ------------------------------------------------------------
# Upload stock exports
# ------------------------------------------------------------
stock_files = st.file_uploader(
    "Upload Farfetch stock exports (HK, US, DE, CH, JP, AU)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

if not stock_files:
    st.stop()

stock_points = ["HK", "US", "DE", "CH", "JP", "AU"]
stock_dfs = {}

for f in stock_files:
    fname = f.name.lower()

    try:
        if fname.endswith(".xlsx"):
            df = pd.read_excel(f, dtype=str)
        else:
            df = pd.read_csv(f, dtype=str)
    except Exception as e:
        st.error(f"Error loading {f.name}: {e}")
        continue

    # required FF headers
    required_ff_cols = ["Product ID", "Partner product ID", "Partner barcode"]
    missing_ff = [c for c in required_ff_cols if c not in df.columns]
    if missing_ff:
        st.error(f"File {f.name} missing required columns: {missing_ff}")
        st.stop()

    # normalize data
    df["Product ID"] = normalize_series(df["Product ID"])
    df["Partner product ID"] = normalize_series(df["Partner product ID"])
    df["Partner barcode"] = normalize_series(df["Partner barcode"])

    # detect GEO
    geo = None
    for sp in stock_points:
        if sp.lower() in fname:
            geo = sp
            break

    if not geo:
        st.warning(f"Could not detect GEO from filename: {f.name}")
        continue

    stock_dfs[geo] = df

    st.subheader(f"{geo} Stock Preview")
    st.dataframe(df.head(5))

if not stock_dfs:
    st.error("No valid stock export files loaded.")
    st.stop()


# ------------------------------------------------------------
# Run matching
# ------------------------------------------------------------
if st.button("Run Farfetch Check"):

    results = assort.copy()

    # Output columns
    for sp in stock_points:
        results[f"{sp}_FF_ID"] = ""
        results[f"{sp}_FOUND_VIA"] = ""

    # Loop over GEOs
    for sp in stock_points:
        if sp not in stock_dfs:
            continue

        df = stock_dfs[sp]

        # Fast lookup dictionaries
        sku_map = {}
        partner_map = {}

        for _, row in df.iterrows():
            pb = row["Partner barcode"]
            pp = row["Partner product ID"]
            pid = row["Product ID"]

            if pb not in sku_map:
                sku_map[pb] = pid

            if pp not in partner_map:
                partner_map[pp] = pid

        # Matching logic per product
        for idx, r in results.iterrows():

            sku = r["SKU"]
            netta = r["Netta product ID"]
            opt = r["Optional product ID"]

            # 1) Try SKU → Partner barcode
            if sku in sku_map:
                results.at[idx, f"{sp}_FF_ID"] = sku_map[sku]
                results.at[idx, f"{sp}_FOUND_VIA"] = "SKU"
                continue

            # 2) Try Netta → Partner product ID
            if netta in partner_map:
                results.at[idx, f"{sp}_FF_ID"] = partner_map[netta]
                results.at[idx, f"{sp}_FOUND_VIA"] = "NETTA"
                continue

            # 3) Try Optional → Partner product ID
            if opt in partner_map:
                results.at[idx, f"{sp}_FF_ID"] = partner_map[opt]
                results.at[idx, f"{sp}_FOUND_VIA"] = "OPTIONAL"
                continue

            # Not found
            results.at[idx, f"{sp}_FOUND_VIA"] = "NOT FOUND"

    st.success("Matching complete!")

    st.dataframe(results)

    # Download CSV
    st.download_button(
        "Download Results CSV",
        results.to_csv(index=False).encode("utf-8"),
        "farfetch_results.csv",
        "text/csv"
    )
