import streamlit as st
import pandas as pd
import plotly.express as px

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="Dashboard Maytag Series 6 – Xtronic",
    layout="wide",
)

st.title("Dashboard Maytag Series 6 – Xtronic")
st.markdown(
    """
    Monitoreo de desempeño de pruebas **CD (secadoras)** y **CW (lavadoras)**  
    • % de fallas por tipo de producto, por FVT y por semana  
    • % de lecturas **fuera de límites de control** para pruebas GetAngle  
    """
)

# --------------------------------------------------
# PATHS DE ARCHIVOS
# --------------------------------------------------
DATA_PATH = "maytag_dashboardFinal_data.csv"
SUMMARY_PATH = "getangle_summary_v2.csv"


# --------------------------------------------------
# LOADERS CON CACHE
# --------------------------------------------------
@st.cache_data
def load_main_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Normalizar columnas clave
    if "FVT" in df.columns:
        df["FVT"] = df["FVT"].astype(str)
    if "BaseType" in df.columns:
        df["BaseType"] = df["BaseType"].astype(str)

    # Columna Fail: 1 si Status = 'FAILED'
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

    # Columna Week a partir de Date (si existe)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Week"] = df["Date"].dt.to_period("W").dt.start_time
    else:
        df["Week"] = pd.NaT

    return df


@st.cache_data
def load_getangle_summary(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Asegurarnos de que las columnas clave existan
    expected_cols = {"FVT", "BaseType", "Test"}
    missing = expected_cols.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en getangle_summary: {missing}")

    df["FVT"] = df["FVT"].astype(str)
    df["BaseType"] = df["BaseType"].astype(str)
    df["Test"] = df["Test"].astype(str)

    # Columna de porcentaje fuera de límites
    if "Percent_out_of_limits" in df.columns:
        df["Percent_out_of_limits"] = df["Percent_out_of_limits"].astype(float)
    elif "Percent" in df.columns:
        df["Percent_out_of_limits"] = df["Percent"].astype(float)
    else:
        raise ValueError(
            "No encuentro la columna 'Percent_out_of_limits' ni 'Percent' "
            "en getangle_summary_v2.csv"
        )

    # Crear columna en porcentaje 0–100
    df["Percent_out_of_limits_pct"] = df["Percent_out_of_limits"] * 100.0

    return df


# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
data = load_main_data(DATA_PATH)
getangle_summary = load_getangle_summary(SUMMARY_PATH)

# --------------------------------------------------
# CÁLCULOS GLOBALES CD vs CW
# --------------------------------------------------
failure_by_product = (
    data.groupby("BaseType")["Fail"]
    .mean()
    .reset_index(name="FailRate")
)
failure_by_product["FailRate_pct"] = 100 * failure_by_product["FailRate"]

# Para mostrar en el resumen rápido
def get_rate_for(bt: str):
    s = failure_by_product.loc[failure_by_product["BaseType"] == bt, "FailRate_pct"]
    return float(s.iloc[0]) if not s.empty else None


cd_rate = get_rate_for("CD")
cw_rate = get_rate_for("CW")

# --------------------------------------------------
# SIDEBAR: FILTROS PRINCIPALES
# --------------------------------------------------
st.sidebar.header("Filtros principales")

product_type = st.sidebar.radio(
    "Selecciona el producto",
    sorted(data["BaseType"].dropna().unique()),
    help="CD = secadoras, CW = lavadoras",
)

subset = data[data["BaseType"] == product_type].copy()

fvt_options = sorted(subset["FVT"].dropna().unique())
fvt_selected = st.sidebar.multiselect(
    "Selecciona FVT",
    options=fvt_options,
    default=fvt_options,
)

if fvt_selected:
    subset = subset[subset["FVT"].isin(fvt_selected)]

# --------------------------------------------------
# MÉTRICAS PRINCIPALES
# --------------------------------------------------
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
    lines = []
    if cd_rate is not None:
        lines.append(f"- CD: **{cd_rate:.2f}%**")
    if cw_rate is not None:
        lines.append(f"- CW: **{cw_rate:.2f}%**")
    if lines:
        st.markdown("\n".join(lines))
    else:
        st.info("Aún no hay información global de CD/CW.")

st.markdown("---")

# --------------------------------------------------
# GRAFICAS: % DE FALLAS POR FVT Y TENDENCIA SEMANAL
# --------------------------------------------------
col_bottom1, col_bottom2 = st.columns(2)

# 1) Barras por FVT
with col_bottom1:
    st.subheader("Porcentaje de fallas por FVT")

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
            labels={"FVT": "Modelo FVT", "FailRate_pct": "% de fallas"},
        )
        fig_fvt.update_traces(
            text=failure_by_fvt.sort_values("FailRate_pct", ascending=False)["FailRate_pct"].round(2),
            texttemplate="%{text:.2f}%",
            textposition="outside",
        )
        fig_fvt.update_layout(
            yaxis_title="% de fallas",
            height=380,
            margin=dict(l=20, r=20, t=10, b=40),
        )
        st.plotly_chart(fig_fvt, use_container_width=True)
    else:
        st.info("No hay datos para los filtros seleccionados.")

# 2) Tendencia semanal
with col_bottom2:
    st.subheader("Tendencia de fallas por semana")

    failure_over_time = (
        subset.groupby("Week")["Fail"]
        .mean()
        .reset_index(name="FailRate")
    )
    failure_over_time["FailRate_pct"] = 100 * failure_over_time["FailRate"]

    # Quitar semanas sin fecha
    failure_over_time = failure_over_time.dropna(subset=["Week"])

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
            margin=dict(l=20, r=20, t=10, b=40),
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No hay datos con fecha para los filtros seleccionados.")

st.markdown("---")

# --------------------------------------------------
# SECCIÓN: LÍMITES DE CONTROL – GETANGLE
# --------------------------------------------------
st.subheader("Análisis de límites de control – Pruebas GetAngle")

# Filtros específicos para límites
col_lim_1, col_lim_2 = st.columns(2)

with col_lim_1:
    fvt_limits = sorted(getangle_summary["FVT"].dropna().unique())
    fvt_sel_limits = st.selectbox(
        "Selecciona FVT para ver % fuera de límites",
        options=fvt_limits,
    )

with col_lim_2:
    base_types_limits = sorted(getangle_summary["BaseType"].dropna().unique())
    base_sel_limits = st.selectbox(
        "Selecciona tipo de producto (BaseType)",
        options=base_types_limits,
    )

summary_filtered = getangle_summary[
    (getangle_summary["FVT"] == fvt_sel_limits)
    & (getangle_summary["BaseType"] == base_sel_limits)
].copy()

if summary_filtered.empty:
    st.info("No hay datos de límites para esa combinación de FVT y BaseType.")
else:
    # Ordenar por % fuera de límites desc
    summary_filtered = summary_filtered.sort_values(
        "Percent_out_of_limits_pct", ascending=False
    )

    fig_limits = px.bar(
        summary_filtered,
        x="Test",
        y="Percent_out_of_limits_pct",
        labels={
            "Test": "Prueba GetAngle",
            "Percent_out_of_limits_pct": "% fuera de límites",
        },
    )
    fig_limits.update_traces(
        text=summary_filtered["Percent_out_of_limits_pct"].round(1),
        texttemplate="%{text:.1f}%",
        textposition="outside",
    )
    fig_limits.update_layout(
        yaxis_title="% fuera de límites",
        height=430,
        margin=dict(l=20, r=20, t=10, b=80),
    )
    st.plotly_chart(fig_limits, use_container_width=True)



