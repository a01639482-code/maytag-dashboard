import streamlit as st
import pandas as pd
import plotly.express as px

# --------- CONFIGURACIÓN GLOBAL ---------
PRIMARY_COLOR = "#2459a6"

st.set_page_config(
    page_title="Dashboard Maytag Series 6",
    layout="wide",
)

st.title("Dashboard Maytag Series 6 – Xtronic")

# --------- CARGA DE DATOS ---------
@st.cache_data
def load_data(path: str):
    # Leemos el CSV ligero con Date ya incluida
    df = pd.read_csv(path, parse_dates=["Date"])

    df["BaseType"] = df["BaseType"].astype(str)
    df["FVT"] = df["FVT"].astype(str)

    # Columna de falla: 1 = Failed, 0 = lo demás
    df["Fail"] = (
        df["Status"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("FAILED")
        .astype(int)
    )

    # Semana de la prueba
    df["Week"] = df["Date"].dt.to_period("W").dt.start_time

    return df


DATA_PATH = "maytag_dashboardFinal_data.csv"
data = load_data(DATA_PATH)

# --------- CÁLCULOS GLOBALES CD vs CW ---------
failure_by_product = (
    data.groupby("BaseType")["Fail"]
        .mean()
        .reset_index(name="FailRate")
)
failure_by_product["FailRate_pct"] = 100 * failure_by_product["FailRate"]

cd_rate = failure_by_product.loc[
    failure_by_product["BaseType"] == "CD", "FailRate_pct"
]
cw_rate = failure_by_product.loc[
    failure_by_product["BaseType"] == "CW", "FailRate_pct"
]
cd_rate = float(cd_rate.iloc[0]) if not cd_rate.empty else None
cw_rate = float(cw_rate.iloc[0]) if not cw_rate.empty el_

