import streamlit as st
import pandas as pd

st.set_page_config(page_title="Farfetch Stock Checker", layout="wide")
st.title("Farfetch Stock Checker")

st.markdown("""
Upload your assortment CSV and the 6 Farfetch stock point CSVs. The tool will check each SKU in your assortment against the stock point files and return which stock points it exists in, using the following order:
1. SKU
2. Netta Product ID
3. Optional Product ID
""")

# --- Upload Assortment CSV ---
assortment_file = st.file_uploader("Upload Assortment CSV", type=["csv"])
if assortment_file is not None:
    assortment_df = pd.read_csv(assortment_file)
    
    # Ensure required columns exist
    required_cols = ['SKU', 'Netta product ID', 'Optional product ID']
    for col in required_cols:
        if col not in assortment_df.columns:
            st.error(f"Assortment CSV must contain column: {col}")
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
        if 'hk' in filename:
            stock_dfs['HK'] = df
        elif 'us' in filename:
            stock_dfs['US'] = df
        elif 'de' in filename:
            stock_dfs['DE'] = df
        elif 'ch' in filename:
            stock_dfs['CH'] = df
        elif 'jp' in filename:
            stock_dfs['JP'] = df
        elif 'au' in filename:
            stock_dfs['AU'] = df
    
    missing_points = [pt for pt in ['HK','US','DE','CH','JP','AU'] if pt not in stock_dfs]
    if missing_points:
        st.warning(f"Missing stock point CSVs for: {', '.join(missing_points)}. You can continue, unmatched points will remain empty.")

    if st.button("Process Files"):
        # Prepare output dataframe
        output_df = assortment_df.copy()
        output_df['found_via'] = 'none'
        
        # Initialize stock point columns
        for sp in ['HK','US','DE','CH','JP','AU']:
            output_df[f'{sp}_ffid'] = ''
        
        # Function to search in a stock dataframe
        def search_stock(stock_df, col, value):
            if pd.isna(value):
                return None
            match = stock_df[stock_df[col] == value]
            if not match.empty:
                return match['Product ID '].astype(str).tolist()  # Farfetch product ID column
            return None
        
        # Process each row
        for idx, row in output_df.iterrows():
            found = False
            # Step 1: check SKU
            for sp, df in stock_dfs.items():
                ffids = search_stock(df, 'Partner barcode ', row['SKU'])
                if ffids:
                    output_df.at[idx, f'{sp}_ffid'] = ','.join(ffids)
                    found = True
            if found:
                output_df.at[idx, 'found_via'] = 'SKU'
                continue
            # Step 2: check Netta Product ID
            for sp, df in stock_dfs.items():
                ffids = search_stock(df, 'Partner product ID ', row['Netta product ID'])
                if ffids:
                    output_df.at[idx, f'{sp}_ffid'] = ','.join(ffids)
                    found = True
            if found:
                output_df.at[idx, 'found_via'] = 'Netta Product ID'
                continue
            # Step 3: check Optional Product ID
            for sp, df in stock_dfs.items():
                ffids = search_stock(df, 'Partner product ID ', row['Optional product ID'])
                if ffids:
                    output_df.at[idx, f'{sp}_ffid'] = ','.join(ffids)
                    found = True
            if found:
                output_df.at[idx, 'found_via'] = 'Optional Product ID'
        
        st.success("Processing complete!")
        st.dataframe(output_df)
        
        # Download button
        csv = output_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Result CSV",
            data=csv,
            file_name="farfetch_checked.csv",
            mime='text/csv'
        )
