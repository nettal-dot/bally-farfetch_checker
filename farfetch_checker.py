import streamlit as st
import pandas as pd

st.set_page_config(page_title="Farfetch Stock Checker", layout="wide")
st.title("Farfetch Stock Checker")

st.markdown("""
Upload your assortment CSV and the 6 Farfetch stock point CSVs.

Checks order:
1. SKU  
2. Netta Product ID  
3. Optional Product ID  

Notes indicate when SKU is missing but IDs exist.  
Summary columns report existence/missing (only US, AU, HK, CH).
""")

# --- Upload Assortment CSV ---
assortment_file = st.file_uploader("Upload Assortment CSV", type=["csv"])
if assortment_file is not None:
    assortment_df = pd.read_csv(assortment_file, dtype=str)
    assortment_df.columns = assortment_df.columns.str.strip()
    # strip all values
    for col in ['SKU', 'Netta product ID', 'Optional product ID']:
        assortment_df[col] = assortment_df[col].astype(str).str.strip()
    
    # Check required columns
    required_cols = ['SKU', 'Netta product ID', 'Optional product ID']
    missing_cols = [col for col in required_cols if col not in assortment_df.columns]
    if missing_cols:
        st.error(f"Assortment CSV missing columns: {', '.join(missing_cols)}")
        st.stop()

# --- Upload Stock CSVs ---
st.markdown("Upload 6 stock point CSVs (HK, US, DE, CH, JP, AU).")
stock_files = st.file_uploader("Upload Stock CSVs", type=["csv"], accept_multiple_files=True)

if assortment_file is not None and len(stock_files) > 0:
    stock_dfs = {}
    for f in stock_files:
        filename = f.name.lower()
        df = pd.read_csv(f, dtype=str)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        if 'hk' in filename: stock_dfs['HK'] = df
        elif 'us' in filename: stock_dfs['US'] = df
        elif 'de' in filename: stock_dfs['DE'] = df
        elif 'ch' in filename: stock_dfs['CH'] = df
        elif 'jp' in filename: stock_dfs['JP'] = df
        elif 'au' in filename: stock_dfs['AU'] = df

    missing_points = [pt for pt in ['HK','US','DE','CH','JP','AU'] if pt not in stock_dfs]
    if missing_points:
        st.warning(f"Missing stock point CSVs: {', '.join(missing_points)}")

    if st.button("Process Files"):
        with st.spinner("Processing files..."):
            output_df = assortment_df.copy()
            output_df['found_via'] = 'none'

            for sp in ['HK','US','DE','CH','JP','AU']:
                output_df[f'{sp}_ffid'] = ''
                output_df[f'{sp}_note'] = ''

            ffid_results = {sp:{} for sp in ['HK','US','DE','CH','JP','AU']}

            # --- Search function ---
            def search_stock(stock_df, col, value):
                if col not in stock_df.columns or pd.isna(value):
                    return None
                value_str = str(value).strip()
                match = stock_df[stock_df[col].astype(str).str.strip() == value_str]
                if not match.empty:
                    ffid = str(match['Product ID'].iloc[0]).strip()[:8]  # first FFID, 8 digits
                    return ffid
                return None

            # --- Process each row ---
            for idx, row in output_df.iterrows():
                for sp, df in stock_dfs.items():
                    note_col = f'{sp}_note'
                    # 1) SKU
                    ffid_sku = search_stock(df, 'Partner barcode', row['SKU'])
                    if ffid_sku:
                        ffid_results[sp][idx] = {'sku': ffid_sku, 'id': None}
                        output_df.at[idx, f'{sp}_ffid'] = ffid_sku
                        output_df.at[idx, 'found_via'] = 'SKU'
                        continue
                    # 2) Netta Product ID
                    ffid_net = search_stock(df, 'Partner product ID', row['Netta product ID'])
                    if ffid_net:
                        ffid_results[sp][idx] = {'sku': None, 'id': ffid_net}
                        output_df.at[idx, f'{sp}_ffid'] = ffid_net
                        output_df.at[idx, note_col] = 'Netta ID exists, SKU missing'
                        if output_df.at[idx, 'found_via'] != 'SKU':
                            output_df.at[idx, 'found_via'] = 'Netta Product ID'
                        continue
                    # 3) Optional Product ID
                    ffid_opt = search_stock(df, 'Partner product ID', row['Optional product ID'])
                    if ffid_opt:
                        ffid_results[sp][idx] = {'sku': None, 'id': ffid_opt}
                        output_df.at[idx, f'{sp}_ffid'] = ffid_opt
                        output_df.at[idx, note_col] = 'Optional ID exists, SKU & Netta missing'
                        if output_df.at[idx, 'found_via'] not in ['SKU','Netta Product ID']:
                            output_df.at[idx, 'found_via'] = 'Optional Product ID'

            # --- Summary columns ---
            all_points = ['AU','CH','HK','US','JP','DE']
            missing_only = ['AU','CH','HK','US']
            sku_summary_list = []
            id_summary_list = []

            for idx, row in output_df.iterrows():
                sku_exists, sku_missing = [], []
                id_exists, id_missing = [], []
                for sp in all_points:
                    res = ffid_results.get(sp, {}).get(idx, {})
                    if res.get('sku'):
                        sku_exists.append(sp)
                    elif sp in missing_only:
                        sku_missing.append(sp)
                    if res.get('id'):
                        id_exists.append(sp)
                    elif sp in missing_only:
                        id_missing.append(sp)
                sku_summary = f"SKU exists in: {', '.join(sku_exists) if sku_exists else 'none'}"
                if sku_missing:
                    sku_summary += f". SKU missing from: {', '.join(sku_missing)}"
                id_summary = f"ID exists in: {', '.join(id_exists) if id_exists else 'none'}"
                if id_missing:
                    id_summary += f". ID missing from: {', '.join(id_missing)}"
                sku_summary_list.append(sku_summary)
                id_summary_list.append(id_summary)

            output_df['SKU_summary'] = sku_summary_list
            output_df['ID_summary'] = id_summary_list

            st.success("Processing complete!")
            st.dataframe(output_df)

            csv = output_df.to_csv(index=False, index_label=False).encode('utf-8')
            st.download_button(
                label="Download Result CSV",
                data=csv,
                file_name="farfetch_checked.csv",
                mime='text/csv'
            )
