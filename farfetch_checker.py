import pandas as pd

# ---------- CONFIG ----------
GEO_FILES = {
    "HK": "farfetch_HK.csv",
    "US": "farfetch_US.csv",
    "DE": "farfetch_DE.csv",
    "CH": "farfetch_CH.csv",
    "JP": "farfetch_JP.csv",
    "AU": "farfetch_AU.csv",
}

ASSORTMENT_FILE = "assortment.csv"

# ---------- LOAD ASSORTMENT ----------
assortment_df = pd.read_csv(ASSORTMENT_FILE)

# Keep only needed columns
assortment_df = assortment_df[["SKU", "Netta product ID", "Optional product ID"]]

# ---------- RESULT DF ----------
result_df = assortment_df[["SKU"]].copy()

# ---------- PROCESS EACH GEO ----------
for geo, file_path in GEO_FILES.items():
    geo_df = pd.read_csv(file_path)

    geo_df = geo_df[[
        "Partner barcode",   # SKU
        "Product ID"         # Farfetch Product ID
    ]]

    # Rename for merge
    geo_df = geo_df.rename(columns={
        "Partner barcode": "SKU",
        "Product ID": f"{geo}_Product_ID"
    })

    # Left join so we keep all SKUs from assortment
    result_df = result_df.merge(
        geo_df,
        on="SKU",
        how="left"
    )

# ---------- SAVE / DISPLAY ----------
result_df.to_csv("farfetch_check_output.csv", index=False)

print(result_df.head())
