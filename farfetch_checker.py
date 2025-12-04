import streamlit as st
import pandas as pd

st.title("Farfetch Product Checker")

# ---------------------------
# UPLOAD ASSORTMENT FILE
# ---------------------------
assortment_file = st.file_uploader(
    "Upload Assortment File (Excel or CSV)",
    type=["xlsx", "xls", "csv"]
)

# ---------------------------
# UPLOAD FARFETCH EXPORT FILES
# ---------------------------
uploaded_files = st.file_uploader(
    "Upload Farfetch Export Files (multiple allowed)",
    type=["xlsx", "xls", "csv"],
    accept_multiple_files=True
)

# ---------------------------
# PROCESS ONLY IF BOTH ARE UPLOADED
# ---------------------------
if assortment_file and uploaded_files:

    # -------- LOAD ASSORTMENT ----------
    if assortment_file.name.endswith(".csv"):
        df_assort = pd.read_csv(assortment_file)
    else:
        df_assort = pd.read_excel(assortment_file)

    # Required assortment headers
    expected_assort_headers = ["SKU", "Netta product ID", "Optional product ID"]

    df_assort.columns = df_assort.columns.str.strip()

    missing = [c for c in expected_assort_headers if c not in df_assort.columns]
    if missing:
        st.error(f"Missing expected assortment headers: {missing}")
        st.stop()

    # -------- LOAD FARFETCH STOCK FILES ----------
    stock_data = {}
    for file in uploaded_files:
        stock_point = file.name.split(".")[0]

        if file.name.endswith(".csv"):
            df_stock = pd.read_csv(file)
        else:
            df_stock = pd.read_excel(file)

        df_stock.columns = df_stock.columns.str.strip()

        required_cols = ["Product ID", "Partner product ID", "Partner barcode"]
        missing_cols = [c for c in required_cols if c not in df_stock.columns]
        if missing_cols:
            st.error(f"{stock_point} is missing required columns: {missing_cols}")
            st.stop()

        stock_data[stock_point] = df_stock[
            ["Product ID", "Partner product ID", "Partner barcode"]
        ].copy()

    # ---------------------------
    # SEARCH LOGIC
    # ---------------------------
    result_rows = []

    for idx, row in df_assort.iterrows():
        sku = str(row["SKU"]).strip()
        netta_id = str(row["Netta product ID"]).strip()
        optional_id = str(row["Optional product ID"]).strip()

        sku_results = {}
        pid_results = {}

        for stock, df in stock_data.items():

            # 1️⃣ SEARCH BY SKU
            df_sku = df[df["Partner barcode"] == sku]
            if not df_sku.empty:
                ff_id = df_sku["Product ID"].iloc[0]
                sku_results[stock] = ff_id
                pid_results[stock] = ff_id
                continue  # STOP checking — SKU found!

            # 2️⃣ SEARCH BY NETTA PRODUCT ID
            df_netta = df[df["Partner product ID"] == netta_id]
            if not df_netta.empty:
                ff_id = df_netta["Product ID"].iloc[0]
                sku_results[stock] = ""
                pid_results[stock] = ff_id
                continue

            # 3️⃣ SEARCH BY OPTIONAL PRODUCT ID
            df_opt = df[df["Partner product ID"] == optional_id]
            if not df_opt.empty:
                ff_id = df_opt["Product ID"].iloc[0]
                sku_results[stock] = ""
                pid_results[stock] = ff_id
                continue

            # Not found anywhere
            sku_results[stock] = ""
            pid_results[stock] = ""

        # SUMMARY RULE:
        # Missing only matters for AU, CH, HK, US
        summary_markets = ["AU", "CH", "HK", "US"]

        sku_exists = [sp for sp in sku_results if sku_results[sp] != ""]
        sku_missing = [sp for sp in summary_markets if sku_results.get(sp, "") == ""]

        pid_exists = [sp for sp in pid_results if pid_results[sp] != ""]
        pid_missing = [sp for sp in summary_markets if pid_results.get(sp, "") == ""]

        result_rows.append({
            "SKU": sku,
            **{f"{sp} FF ID (SKU search)": sku_results[sp] for sp in stock_data},
            **{f"{sp} FF ID (Product ID search)": pid_results[sp] for sp in stock_data},
            "SKU exists in": ", ".join(sku_exists),
            "SKU missing from": ", ".join(sku_missing),
            "Product ID exists in": ", ".join(pid_exists),
            "Product ID missing from": ", ".join(pid_missing),
        })

    final_df = pd.DataFrame(result_rows)

    st.success("Processing complete!")
    st.dataframe(final_df, use_container_width=True)

    # Option to download
    st.download_button(
        "Download Results as CSV",
        final_df.to_csv(index=False).encode("utf-8"),
        "farfetch_results.csv",
        "text/csv"
    )
