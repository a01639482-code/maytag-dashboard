import streamlit as st
import pandas as pd
import plotly.express as px

# --------- CARGA DE DATOS ---------
@st.cache_data
def load_data(path: str):
    df = pd.read_csv(path, parse_dates=["Date"])

    df["BaseType"] = df["BaseType"].astype(str)
    df["FVT"] = df["FVT"].astype(str)

    df["Fail"] = (
        df["Status"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("FAILED")
        .astype(int)
    )

    df["Week"] = df["Date"].dt.to_period("W").dt.start_time

    return df


# --------- CONFIGURACIÓN ---------
st.set_page_config(
    page_title="Dashboard Maytag Series 6",
    layout="wide",
)

st.title("Dashboard Maytag Series 6 – Xtronic")

DATA_PATH = "maytag_dashboard_data.csv"
data = load_data(DATA_PATH)

# --------- MÉTRICAS GLOBALES ---------
failure_by_product = (
    data.groupby("BaseType")["Fail"]
        .mean()
        .reset_index(name="FailRate")
)
failure_by_product["FailRate_pct"] = 100 * failure_by_product["FailRate"]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Porcentaje de fallas por tipo de producto (CD vs CW)")
    fig_product = px.bar(
        failure_by_product,
        x="BaseType",
        y="FailRate_pct",
        text="FailRate_pct",
        labels={"BaseType": "Producto", "FailRate_pct": "% de fallas"},
    )
    fig_product.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    st.plotly_chart(fig_product, use_container_width=True)

with col2:
    st.subheader("Resumen rápido")
    for _, row in failure_by_product.iterrows():
        st.metric(
            label=f"{row['BaseType']} - % fallas",
            value=f"{row['FailRate_pct']:.2f}%",
        )

st.markdown("---")

# --------- SIDEBAR ---------
st.sidebar.header("Filtros")

product_type = st.sidebar.radio(
    "Selecciona el producto",
    sorted(data["BaseType"].unique()),
    help="CD = secadoras, CW = lavadoras",
)

subset = data[data["BaseType"] == product_type].copy()

fvt_selected = st.sidebar.multiselect(
    "Selecciona FVT",
    sorted(subset["FVT"].unique()),
    default=sorted(subset["FVT"].unique())
)

if fvt_selected:
    subset = subset[subset["FVT"].isin(fvt_selected)]

st.subheader(f"Análisis detallado para {product_type}")

# --------- FALLAS POR FVT ---------
failure_by_fvt = (
    subset.groupby("FVT")["Fail"]
          .mean()
          .reset_index(name="FailRate")
)
failure_by_fvt["FailRate_pct"] = 100 * failure_by_fvt["FailRate"]

st.markdown("### Porcentaje de fallas por FVT")
fig_fvt = px.bar(
    failure_by_fvt.sort_values("FailRate_pct", ascending=False),
    x="FVT",
    y="FailRate_pct",
    text="FailRate_pct",
    labels={"FVT": "Modelo FVT", "FailRate_pct": "% de fallas"},
)
fig_fvt.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
st.plotly_chart(fig_fvt, use_container_width=True)

# --------- TENDENCIA SEMANAL ---------
failure_over_time = (
    subset.groupby("Week")["Fail"]
          .mean()
          .reset_index(name="FailRate")
)
failure_over_time["FailRate_pct"] = 100 * failure_over_time["FailRate"]

st.markdown("### Tendencia de fallas por semana")

fig_time = px.line(
    failure_over_time,
    x="Week",
    y="FailRate_pct",
    markers=True,
    labels={"Week": "Semana", "FailRate_pct": "% de fallas"},
)
st.plotly_chart(fig_time, use_container_width=True)
