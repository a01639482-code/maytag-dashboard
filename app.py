import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIGURACIÓN DE PÁGINA
# =========================
st.set_page_config(
    page_title="Dashboard Maytag Series 6",
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
# RUTINAS DE CARGA DE DATOS
# =========================

DATA_PATH = "maytag_dashboardFinal_data.csv"
SUMMARY_PATH = "getangle_summary_v2.csv"


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    """Lee la base principal de pruebas (CD/CW)."""
    df = pd.read_csv(path, parse_dates=["Date"])

    # Normalizar columnas clave
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

    # Semana de la prueba
    if "Date" in df.columns:
        df["Week"] = df["Date"].dt.to_period("W").dt.start_time
    else:
        df["Week"] = pd.NaT

    return df


@st.cache_data
def load_getangle_summary(path: str) -> pd.DataFrame:
    """
    Lee el resumen de límites para GetAngle.
    NO lanza errores si algo viene raro; solo limpia nombres.
    """
    df = pd.read_csv(path)

    # Quitar espacios en blanco por si vienen columnas con espacio al final
    df.columns = df.columns.str.strip()

    # Normalizar nombres típicos con espacios
    rename_map = {
        "BaseType ": "BaseType",
        "Test ": "Test",
        "Percent_out_of_limits ": "Percent_out_of_limits",
    }
    df = df.rename(columns=rename_map)

    # Normalizar tipos
    if "FVT" in df.columns:
        df["FVT"] = df["FVT"].astype(str)
    if "BaseType" in df.columns:
        df["BaseType"] = df["BaseType"].astype(str)

    # Si la columna de porcentaje no existe, la creamos en 0 para no tronar
    if "Percent_out_of_limits" not in df.columns:
        df["Percent_out_of_limits"] = 0.0

    return df


# =========================
# CARGA
# =========================

data = load_data(DATA_PATH)
getangle_summary = load_getangle_summary(SUMMARY_PATH)

# =========================
# CÁLCULOS GLOBALES CD vs CW
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
# SIDEBAR: FILTROS
# =========================

st.sidebar.header("Filtros")

# Tipo de producto (CD / CW)
product_type = st.sidebar.radio(
    "Selecciona el producto",
    sorted(data["BaseType"].unique()),
    help="CD = secadoras, CW = lavadoras",
)

subset = data[data["BaseType"] == product_type].copy()

# Filtro de FVTs
lista_fvt = sorted(subset["FVT"].unique())
fvt_selected = st.sidebar.multiselect(
    "Selecciona FVT",
    lista_fvt,
    default=lista_fvt,
)

if fvt_selected:
    subset = subset[subset["FVT"].isin(fvt_selected)]

# =========================
# MÉTRICA PRINCIPAL
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
        txt = f"- CD: **{cd_rate:.2f}%**\n- CW: **{cw_rate:.2f}%**"
    elif cd_rate is not None:
        txt = f"- CD: **{cd_rate:.2f}%**"
    elif cw_rate is not None:
        txt = f"- CW: **{cw_rate:.2f}%**"
    else:
        txt = "No hay información global."
    st.markdown(txt)

st.markdown("---")

# =========================
# GRÁFICAS PRINCIPALES (2 columnas)
# =========================

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
            texttemplate="%{text:.2f}%",
            textposition="outside",
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

# =========================
# NUEVA SECCIÓN: % FUERA DE LÍMITES GETANGLE
# =========================

st.markdown("### % de lecturas fuera de límites de control (GetAngle)")

# Filtrar el resumen por producto y FVTs seleccionados
summary_filtered = getangle_summary.copy()
summary_filtered = summary_filtered[
    (summary_filtered["BaseType"] == product_type)
]

if fvt_selected:
    summary_filtered = summary_filtered[
        summary_filtered["FVT"].isin(fvt_selected)
    ]

if not summary_filtered.empty:
    # Convertir a %
    summary_filtered["Percent_out_of_limits_pct"] = (
        summary_filtered["Percent_out_of_limits"] * 100.0
    )

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
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )
    fig_limits.update_layout(
        yaxis_title="% fuera de límites",
        height=420,
        margin=dict(l=20, r=20, t=40, b=40),
    )
    st.plotly_chart(fig_limits, use_container_width=True)
else:
    st.info(
        "No hay información de límites para la combinación de producto y FVT seleccionada."
    )
