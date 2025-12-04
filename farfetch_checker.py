import pandas as pd
import streamlit as st

# -----------------------------
# Streamlit app
# -----------------------------
st.title("Farfetch SKU Checker")

# Upload files
assortment_file = st.file_uploader("Upload Assortment File (Excel/CSV)", type=["xlsx", "csv"])
stock_files = st.file_uploader("Upload Stock Export Files (one per stock point, Excel/CSV, name must include stock point)", type=["xlsx", "csv"], accept_multiple_files=True)

if assortment_file and stock_files:
    # Read assortment file
    if assortment_file.name.endswith('.xlsx'):
        df_assortment = pd.read_excel(assortment_file)
    else:
        df_assortment = pd.read_csv(assortment_file)

    # Ensure columns exist
    expected_cols = ['SKU', 'Netta Product ID', 'Optional Product ID']
    for col in expected_cols:
        if col not in df_assortment.columns:
            st.error(f"Assortment file missing required column: {col}")
            st.stop()
    
    # Read stock exports
    stock_data = {}
    for f in stock_files:
        if f.name.endswith('.xlsx'):
            df_stock = pd.read_excel(f)
        else:
            df_stock = pd.read_csv(f)

        # Determine stock point from file name (e.g., "HK_stock.xlsx")
        stock_point = f.name.split('_')[0].upper()
        stock_data[stock_point] = df_stock[['H', 'A', 'F']].rename(columns={
            'H': 'SKU',
            'A': 'FF_ID',
            'F': 'Product_ID'
        })

    # Initialize output dataframe
    output = df_assortment.copy()
    
    stock_points = ['HK', 'US', 'DE', 'CH', 'JP', 'AU']
    for sp in stock_points:
        ff_ids = []
        for idx, row in df_assortment.iterrows():
            df_sp = stock_data.get(sp)
            if df_sp is None:
                ff_ids.append(None)
                continue
            
            # Check SKU
            match_sku = df_sp[df_sp['SKU'] == row['SKU']]
            if not match_sku.empty:
                ff_ids.append(match_sku['FF_ID'].iloc[0])
            else:
                # Check Netta Product ID
                match_net = df_sp[df_sp['Product_ID'] == row['Netta Product ID']]
                if not match_net.empty:
                    ff_ids.append(match_net['FF_ID'].iloc[0])
                else:
                    # Check Optional Product ID
                    match_opt = df_sp[df_sp['Product_ID'] == row['Optional Product ID']]
                    if not match_opt.empty:
                        ff_ids.append(match_opt['FF_ID'].iloc[0])
                    else:
                        ff_ids.append(None)
        output[sp] = ff_ids

    # -----------------------------
    # Create summary columns
    # -----------------------------
    def sku_summary(row):
        exists = []
        missing = []
        for sp in ['AU', 'CH', 'HK', 'US']:  # Only consider these for summary
            if pd.notna(row[sp]):
                exists.append(sp)
            else:
                missing.append(sp)
        return f"SKU exists in: {', '.join(exists)}. SKU missing from: {', '.join(missing)}"

    def product_id_summary(row):
        exists = []
        missing = []
        for sp in ['AU', 'CH', 'HK', 'US']:
            if pd.notna(row[sp]):
                exists.append(sp)
            else:
                missing.append(sp)
        return f"Product ID exists in: {', '.join(exists)}. Product ID missing from: {', '.join(missing)}"

    output['SKU Summary'] = output.apply(sku_summary, axis=1)
    output['Product ID Summary'] = output.apply(product_id_summary, axis=1)

    # Display the result
    st.dataframe(output)

    # Allow download
    csv = output.to_csv(index=False).encode('utf-8')
    st.download_button("Download Result as CSV", csv, "farfetch_check_result.csv", "text/csv")
