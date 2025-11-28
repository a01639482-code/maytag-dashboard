import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
#  CARGA DE DATOS PRINCIPAL
# =========================
@st.cache_data
def load_main_data(path: str) -> pd.DataFrame:
    """Lee la base principal de pruebas (CD/CW)."""
    df = pd.read_csv(path, parse_dates=["Date"])

    # Asegurar tipos de columnas clave
    if "BaseType" in df.columns:
        df["BaseType"] = df["BaseType"].astype(str)

    if "FVT" in df.columns:
        df["FVT"] = df["FVT"].astype(str)

    # Columna de falla: 1 = Failed, 0 = lo demás
    if "Status" in df.columns:
        df["Fail"] = (
            df["Status"]
            .astype(str)
            .str.strip()
            .str.upper()
            .eq("FAILED")
            .astype(int)
        )
    else:
        df["Fail"] = 0

    # Semana de la prueba (inicio de semana)
    if "Date" in df.columns:
        df["Week"] = df["Date"].dt.to_period("W").dt.start_time
    else:
        df["Week"] = pd.NaT

    return df


# ==================================
#  CARGA DE RESUMEN GETANGLE/LÍMITES
# ==================================
@st.cache_data
def load_getangle_summary(path: str) -> pd.DataFrame:
    """
    Lee el resumen de % fuera de límites por FVT / BaseType / Test
    desde getangle_summary_v2.csv.
    """
    df = pd.read_csv(path)

    # Limpiar nombres de columnas por si traen espacios
    df.columns = df.columns.str.strip()

    # Columnas que necesitamos sí o sí
    needed = {"FVT", "BaseType", "Test", "Percent_out_of_limits"}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(
            f"Faltan columnas en getangle_summary_v2.csv: {missing}"
        )

    # Tipos
    df["FVT"] = df["FVT"].astype(str)
    df["BaseType"] = df["BaseType"].astype(str)
    df["Test"] = df["Test"].astype(str)

    # Asegurarnos de tener porcentaje en 0–100
    # Si viene 0–1 lo convertimos, si ya viene 0–100 lo dejamos igual
    max_val = df["Percent_out_of_limits"].max()
    if max_val <= 1.5:
        df["Percent_out_of_limits_pct"] = (
            df["Percent_out_of_limits"] * 100.0
        )
    else:
        df["Percent_out_of_limits_pct"] = df["Percent_out_of_limits"]

    return df


# =========================
#  CONFIGURACIÓN DE PÁGINA
# =========================
st.set_page_config(
    page_title="Dashboard Maytag Series 6 – Xtronic",
    layout="wide",
)

st.title("Dashboard Maytag Series 6 – Xtronic")
st.markdown(
    """
Monitoreo de desempeño de pruebas **CD (secadoras)** y **CW (lavadoras)**

- % de fallas por tipo de producto, por FVT y por semana  
- % de lecturas **fuera de límites de control** para pruebas GetAngle
"""
)

# =========================
#  RUTAS DE ARCHIVOS
# =========================
DATA_PATH = "maytag_dashboardFinal_data.csv"
SUMMARY_PATH = "getangle_summary_v2.csv"

data = load_data(DATA_PATH)  # 👈 usamos la función que sí existe
getangle_summary = load_getangle_summary(SUMMARY_PATH)

# Cargar datos
data = load_main_data(DATA_PATH)
getangle_summary = load_getangle_summary(SUMMARY_PATH)

# =========================
#  CÁLCULOS GLOBALES CD vs CW
# =========================
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
cw_rate = float(cw_rate.iloc[0]) if not cw_rate.empty else None

# =========================
#        SIDEBAR
# =========================
st.sidebar.header("Filtros")

product_type = st.sidebar.radio(
    "Selecciona el producto",
    sorted(data["BaseType"].dropna().unique()),
    help="CD = secadoras, CW = lavadoras",
)

subset = data[data["BaseType"] == product_type].copy()

fvt_selected = st.sidebar.multiselect(
    "Selecciona FVT",
    sorted(subset["FVT"].dropna().unique()),
    default=sorted(subset["FVT"].dropna().unique()),
)

if fvt_selected:
    subset = subset[subset["FVT"].isin(fvt_selected)]

# =========================
#  MÉTRICA PRINCIPAL FALLAS
# =========================
selected_fail_rate = subset["Fail"].mean() * 100 if len(subset) > 0 else 0.0

col_top1, col_top2 = st.columns([2, 1])

with col_top1:
    st.subheader(f"{product_type} – porcentaje de fallas")
    st.metric(
        label=f"% de fallas {product_type}",
        value=f"{selected_fail_rate:.2f} %",
    )

with col_top2:
    st.subheader("Comparativo general CD vs CW")
    txt = ""
    if cd_rate is not None and cw_rate is not None:
        txt = f"- **CD:** {cd_rate:.2f}%\n- **CW:** {cw_rate:.2f}%"
    elif cd_rate is not None:
        txt = f"- **CD:** {cd_rate:.2f}%"
    elif cw_rate is not None:
        txt = f"- **CW:** {cw_rate:.2f}%"
    else:
        txt = "Sin información suficiente."
    st.markdown(txt)

st.markdown("---")

# =======================================
#  FILA 1: FALLAS POR FVT Y POR SEMANA
# =======================================
col_bottom1, col_bottom2 = st.columns(2)

# ---- Izquierda: Barras por FVT ----
with col_bottom1:
    st.markdown("### Porcentaje de fallas por FVT")

    failure_by_fvt = (
        subset.groupby("FVT")["Fail"]
        .mean()
        .reset_index(name="FailRate")
    )
    failure_by_fvt["FailRate_pct"] = 100 * failure_by_fvt["FailRate"]

    if not failure_by_fvt.empty:
        fig_fvt = px.bar(
            failure_by_fvt.sort_values("FailRate_pct", ascending=False),
            x="FVT",
            y="FailRate_pct",
            text="FailRate_pct",
            labels={"FVT": "Modelo FVT", "FailRate_pct": "% de fallas"},
        )
        fig_fvt.update_traces(
            texttemplate="%{text:.2f}%", textposition="outside"
        )
        fig_fvt.update_layout(
            yaxis_title="% de fallas",
            height=380,
            margin=dict(l=20, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_fvt, use_container_width=True)
    else:
        st.info("No hay datos para los filtros seleccionados.")

# ---- Derecha: Tendencia semanal ----
with col_bottom2:
    st.markdown("### Tendencia de fallas por semana")

    failure_over_time = (
        subset.groupby("Week")["Fail"]
        .mean()
        .reset_index(name="FailRate")
    )
    failure_over_time["FailRate_pct"] = 100 * failure_over_time["FailRate"]

    if not failure_over_time.empty:
        fig_time = px.line(
            failure_over_time,
            x="Week",
            y="FailRate_pct",
            markers=True,
            labels={"Week": "Semana", "FailRate_pct": "% de fallas"},
        )
        fig_time.update_layout(
            yaxis_title="% de fallas",
            height=380,
            margin=dict(l=20, r=20, t=40, b=40),
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No hay datos con fecha para los filtros seleccionados.")

st.markdown("---")

# =======================================
#  FILA 2: % FUERA DE LÍMITES (GETANGLE)
# =======================================
st.subheader("Lecturas fuera de límites de control – GetAngle")

col_limits_filters, col_limits_plot = st.columns([1, 3])

with col_limits_filters:
    st.markdown("#### Filtros de límites")

    base_options_limits = sorted(
        getangle_summary["BaseType"].dropna().unique()
    )
    base_selected_limits = st.selectbox(
        "Producto (CD / CW)",
        base_options_limits,
        index=0 if base_options_limits else None,
        key="limits_base",
    )

    subset_limits = getangle_summary[
        getangle_summary["BaseType"] == base_selected_limits
    ]

    fvt_options_limits = sorted(subset_limits["FVT"].dropna().unique())
    fvt_selected_limits = st.selectbox(
        "FVT",
        fvt_options_limits,
        index=0 if fvt_options_limits else None,
        key="limits_fvt",
    )

with col_limits_plot:
    summary_filtered = subset_limits[
        subset_limits["FVT"] == fvt_selected_limits
    ]

    if not summary_filtered.empty:
        fig_limits = px.bar(
            summary_filtered.sort_values(
                "Percent_out_of_limits_pct", ascending=False
            ),
            x="Test",
            y="Percent_out_of_limits_pct",
            text="Percent_out_of_limits_pct",
            labels={
                "Test": "Prueba GetAngle",
                "Percent_out_of_limits_pct": "% fuera de límites",
            },
        )
        fig_limits.update_traces(
            texttemplate="%{text:.1f}%", textposition="outside"
        )
        fig_limits.update_layout(
            height=380,
            margin=dict(l=20, r=20, t=40, b=40),
            xaxis_tickangle=-35,
        )
        st.plotly_chart(fig_limits, use_container_width=True)
    else:
        st.info("No hay información de límites para esa combinación.")
