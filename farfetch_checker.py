import streamlit as st
import pandas as pd

st.set_page_config(page_title="Farfetch Pre-Upload Checker", layout="wide")
st.title("Farfetch Pre-Upload Checker")

# -----------------------------
# FILE UPLOADS
# -----------------------------
assortment_file = st.file_uploader(
    "Upload Assortment CSV",
    type=["csv"]
)

st.subheader("Upload Farfetch Exports by GEO")

geo_uploads = {
    "HK": st.file_uploader("HK Export", type=["csv"]),
    "US": st.file_uploader("US Export", type=["csv"]),
    "DE": st.file_uploader("DE Export", type=["csv"]),
    "CH": st.file_uploader("CH Export", type=["csv"]),
    "JP": st.file_uploader("JP Export", type=["csv"]),
    "AU": st.file_uploader("AU Export", type=["csv"]),
}

# -----------------------------
# PROCESSING
# -----------------------------
if assortment_file and all(geo_uploads.values()):

    # Load assortment
    assortment_df = pd.read_csv(assortment_file)

    required_assortment_cols = {
        "SKU",
        "Netta product ID",
        "Optional product ID"
    }

    if not required_assortment_cols.issubset(assortment_df.columns):
        st.error("Assortment file is missing required columns.")
        st.stop()

    # Prepare result
    result_df = assortment_df[["SKU"]].copy()
    result_df["SKU"] = result_df["SKU"].astype(str).str.strip()

    # Process each GEO
    for geo, uploaded_file in geo_uploads.items():
        geo_df = pd.read_csv(uploaded_file)

        required_geo_cols = {
            "Partner barcode",
            "Product ID"
        }

        if not required_geo_cols.issubset(geo_df.columns):
            st.error(f"{geo} export is missing required columns.")
            st.stop()

        # Keep only necessary columns
        geo_df = geo_df[["Partner barcode", "Product ID"]].copy()

        # Convert SKU to string and strip spaces
        geo_df["Partner barcode"] = geo_df["Partner barcode"].astype(str).str.strip()

        # Rename for merging
        geo_df = geo_df.rename(columns={
            "Partner barcode": "SKU",
            "Product ID": f"{geo}_Product_ID"
        })

        # Merge with result
        result_df = result_df.merge(
            geo_df,
            on="SKU",
            how="left"
        )

    # -----------------------------
    # DISPLAY RESULTS
    # -----------------------------
    st.success("Check completed")
    st.dataframe(result_df, use_container_width=True)

    # -----------------------------
    # DOWNLOAD RESULT
    # -----------------------------
    csv = result_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download result as CSV",
        data=csv,
        file_name="farfetch_pre_upload_check.csv",
        mime="text/csv"
    )

else:
    st.info("Please upload the assortment file and all 6 GEO exports.")
