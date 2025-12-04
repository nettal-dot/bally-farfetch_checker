import pandas as pd
import streamlit as st

st.title("Farfetch SKU Checker (Robust Version)")

# -----------------------------
# Upload files
# -----------------------------
assortment_file = st.file_uploader("Upload Assortment File (Excel/CSV)", type=["xlsx", "csv"])
stock_files = st.file_uploader(
    "Upload Stock Export Files (Excel/CSV, name must include stock point)", 
    type=["xlsx", "csv"], 
    accept_multiple_files=True
)

if assortment_file and stock_files:
    # -----------------------------
    # Read assortment file
    # -----------------------------
    try:
        if assortment_file.name.endswith(".xlsx"):
            df_assortment = pd.read_excel(assortment_file)
        else:
            df_assortment = pd.read_csv(assortment_file)
    except Exception as e:
        st.error(f"Error reading assortment file: {e}")
        st.stop()

    # Check required columns
    required_cols = ['SKU', 'Netta Product ID', 'Optional Product ID']
    for col in required_cols:
        if col not in df_assortment.columns:
            st.error(f"Assortment file missing column: {col}")
            st.stop()

    # Normalize: strip, string, uppercase
    for col in required_cols:
        df_assortment[col] = df_assortment[col].astype(str).str.strip().str.upper()

    # -----------------------------
    # Read stock export files
    # -----------------------------
    stock_data = {}
    required_stock_cols = ['Partner barcode', 'Product ID', 'Partner product ID']
    
    for f in stock_files:
        try:
            if f.name.endswith(".xlsx"):
                df_stock = pd.read_excel(f)
            else:
                df_stock = pd.read_csv(f)
        except Exception as e:
            st.warning(f"Could not read {f.name}: {e}")
            continue

        # Check required columns
        if not all(col in df_stock.columns for col in required_stock_cols):
            st.warning(f"File {f.name} missing required columns: {', '.join(required_stock_cols)}")
            continue

        # Rename and normalize
        df_sp = df_stock[required_stock_cols].rename(columns={
            'Partner barcode': 'SKU',
            'Product ID': 'FF_ID',
            'Partner product ID': 'Product_ID'
        })
        for col in ['SKU', 'Product_ID', 'FF_ID']:
            df_sp[col] = df_sp[col].astype(str).str.strip().str.upper()

        # Determine stock point from filename
        stock_point = f.name.split("_")[0].upper()
        stock_data[stock_point] = df_sp

    if not stock_data:
        st.error("No valid stock export files found.")
        st.stop()

    # -----------------------------
    # Matching logic
    # -----------------------------
    output = df_assortment.copy()
    stock_points = ['HK', 'US', 'DE', 'CH', 'JP', 'AU']

    for sp in stock_points:
        ff_ids = []
        df_sp = stock_data.get(sp)
        for idx, row in df_assortment.iterrows():
            ff_id = None
            if df_sp is not None:
                # Try SKU
                match_sku = df_sp[df_sp['SKU'] == row['SKU']]
                if not match_sku.empty:
                    ff_id = match_sku['FF_ID'].iloc[0]
                else:
                    # Try Netta Product ID
                    match_net = df_sp[df_sp['Product_ID'] == row['Netta Product ID']]
                    if not match_net.empty:
                        ff_id = match_net['FF_ID'].iloc[0]
                    else:
                        # Try Optional Product ID
                        match_opt = df_sp[df_sp['Product_ID'] == row['Optional Product ID']]
                        if not match_opt.empty:
                            ff_id = match_opt['FF_ID'].iloc[0]
            ff_ids.append(ff_id)
        output[sp] = ff_ids

    # -----------------------------
    # Summary columns
    # -----------------------------
    def sku_summary(row):
        exists, missing = [], []
        for sp in ['AU','CH','HK','US']:
            if pd.notna(row[sp]):
                exists.append(sp)
            else:
                missing.append(sp)
        return f"SKU exists in: {', '.join(exists)}. SKU missing from: {', '.join(missing)}"

    def product_id_summary(row):
        exists, missing = [], []
        for sp in ['AU','CH','HK','US']:
            if pd.notna(row[sp]):
                exists.append(sp)
            else:
                missing.append(sp)
        return f"Product ID exists in: {', '.join(exists)}. Product ID missing from: {', '.join(missing)}"

    output['SKU Summary'] = output.apply(sku_summary, axis=1)
    output['Product ID Summary'] = output.apply(product_id_summary, axis=1)

    # -----------------------------
    # Display and download
    # -----------------------------
    st.dataframe(output)

    csv = output.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV", csv, "farfetch_check_result.csv", "text/csv")

    # -----------------------------
    # Debug: show unmatched SKUs
    # -----------------------------
    st.subheader("Debug: SKUs not found in any stock point")
    unmatched = output.loc[output[stock_points].isna().all(axis=1), 'SKU']
    st.write(unmatched)
