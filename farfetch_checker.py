import streamlit as st
import pandas as pd

st.set_page_config(page_title="Farfetch Stock Checker", layout="wide")
st.title("Farfetch Stock Checker")

st.markdown("""
Upload your assortment CSV and the 6 Farfetch stock point CSVs.  
The tool will check each SKU in your assortment against the stock point files and return which stock points it exists in, using the following order per stock point:

1. SKU  
2. Netta Product ID (if SKU missing)  
3. Optional Product ID (if SKU & Netta missing)  

Notes will indicate if SKU is missing but Netta or Optional exists.  
Summary columns at the end show overall SKU and ID existence per stock point.
""")

# --- Upload Assortment CSV ---
assortment_file = st.file_uploader("Upload Assortment CSV", type=["csv"])
assortment_df = None
if assortment_file is not None:
    assortment_df = pd.read_csv(assortment_file)
    assortment_df.columns = assortment_df.columns.str.strip()  # remove spaces

    # Ensure required columns exist
    required_cols = ['SKU', 'Netta product ID', 'Optional product ID']
    missing_cols = [col for col in required_cols if col not in assortment_df.columns]
    if missing_cols:
        st.error(f"Assortment CSV must contain columns: {', '.join(missing_cols)}")
        st.stop()

# --- Upload Stock Point CSVs ---
st.markdown("Upload 6 stock point CSVs (HK, US, DE, CH, JP, AU).")
stock_files = st.file_uploader("Upload Stock CSVs", type=["csv"], accept_multiple_files=True)

if assortment_file is not None and len(stock_files) > 0:
    # Load stock point files into a dictionary
    stock_dfs = {}
    for f in stock_files:
        filename = f.name.lower()
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip()  # strip spaces from headers
        if 'hk' in filename: stock_dfs['HK'] = df
        elif 'us' in filename: stock_dfs['US'] = df
        elif 'de' in filename: stock_dfs['DE'] = df
        elif 'ch' in filename: stock_dfs['CH'] = df
        elif 'jp' in filename: stock_dfs['JP'] = df
        elif 'au' in filename: stock_dfs['AU'] = df

    missing_points = [pt for pt in ['HK','US','DE','CH','JP','AU'] if pt not in stock_dfs]
    if missing_points:
        st.warning(f"Missing stock point CSVs for: {', '.join(missing_points)}. You can continue, unmatched points will remain empty.")

    if st.button("Process Files"):
        with st.spinner("Processing files..."):
            # Prepare output dataframe
            output_df = assortment_df.copy()
            output_df['found_via'] = 'none'

            # Initialize stock point FFID and note columns
            for sp in ['HK','US','DE','CH','JP','AU']:
                output_df[f'{sp}_ffid'] = ''
                output_df[f'{sp}_note'] = ''

            # Function to search in a stock dataframe (deduplicated)
            def search_stock(stock_df, col, value):
                if col not in stock_df.columns or pd.isna(value):
                    return None
                match = stock_df[stock_df[col] == value]
                if not match.empty:
                    ffid_list = match['Product ID'].astype(str).tolist()
                    ffid_unique = list(dict.fromkeys(ffid_list))  # remove duplicates, preserve order
                    return ffid_unique
                return None

            # --- Process each row ---
            for idx, row in output_df.iterrows():
                for sp, df in stock_dfs.items():
                    note_col = f'{sp}_note'

                    # Step 1: Check SKU
                    ffids_sku = search_stock(df, 'Partner barcode', row['SKU'])
                    if ffids_sku:
                        output_df.at[idx, f'{sp}_ffid'] = ','.join(ffids_sku)
                        output_df.at[idx, 'found_via'] = 'SKU'
                        continue  # Skip Netta/Optional check for this stock point

                    # Step 2: Check Netta Product ID
                    ffids_net = search_stock(df, 'Partner product ID', row['Netta product ID'])
                    if ffids_net:
                        output_df.at[idx, f'{sp}_ffid'] = ','.join(ffids_net)
                        output_df.at[idx, note_col] = 'Netta ID exists, SKU missing'
                        if output_df.at[idx, 'found_via'] != 'SKU':
                            output_df.at[idx, 'found_via'] = 'Netta Product ID'
                        continue  # Skip Optional check for this stock point

                    # Step 3: Check Optional Product ID
                    ffids_opt = search_stock(df, 'Partner product ID', row['Optional product ID'])
                    if ffids_opt:
                        output_df.at[idx, f'{sp}_ffid'] = ','.join(ffids_opt)
                        output_df.at[idx, note_col] = 'Optional ID exists, SKU & Netta missing'
                        if output_df.at[idx, 'found_via'] not in ['SKU', 'Netta Product ID']:
                            output_df.at[idx, 'found_via'] = 'Optional Product ID'

            # --- Add summary columns ---
            summary_sku_cols = ['AU','CH','HK','US','JP','DE']  # check existence
            summary_sku_missing = ['AU','CH','HK','US']        # only these for missing
            summary_id_cols = ['AU','CH','HK','US','JP','DE']

            sku_summary_list = []
            id_summary_list = []

            for idx, row in output_df.iterrows():
                # --- SKU summary ---
                sku_exists = []
                sku_missing = []
                for sp in summary_sku_cols:
                    ffid_sku = search_stock(stock_dfs.get(sp, pd.DataFrame()), 'Partner barcode', row['SKU'])
                    if ffid_sku:
                        sku_exists.append(sp)
                    elif sp in summary_sku_missing:
                        sku_missing.append(sp)
                sku_summary = f"SKU exists in: {', '.join(sku_exists) if sku_exists else 'none'}"
                if sku_missing:
                    sku_summary += f". SKU missing from: {', '.join(sku_missing)}"
                sku_summary_list.append(sku_summary)

                # --- ID summary (Netta or Optional) ---
                id_exists = []
                id_missing = []
                for sp in summary_id_cols:
                    df_sp = stock_dfs.get(sp, pd.DataFrame())
                    ffid_net = search_stock(df_sp, 'Partner product ID', row['Netta product ID'])
                    ffid_opt = search_stock(df_sp, 'Partner product ID', row['Optional product ID'])
                    if ffid_net or ffid_opt:
                        id_exists.append(sp)
                    else:
                        id_missing.append(sp)
                id_summary = f"ID exists in: {', '.join(id_exists) if id_exists else 'none'}"
                if id_missing:
                    id_summary += f". ID missing from: {', '.join(id_missing)}"
                id_summary_list.append(id_summary)

            output_df['SKU_summary'] = sku_summary_list
            output_df['ID_summary'] = id_summary_list

            st.success("Processing complete!")
            st.dataframe(output_df)

            # --- Download button ---
            csv = output_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Result CSV",
                data=csv,
                file_name="farfetch_checked.csv",
                mime='text/csv'
            )
