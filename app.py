import streamlit as st
import pandas as pd
import plotly.express as px

# --------- CARGA DE DATOS PRINCIPALES ---------
@st.cache_data
def load_data(path: str):
    df = pd.read_csv(path, parse_dates=["Date"])

    # Asegurar tipos
    df["BaseType"] = df["BaseType"].astype(str)
    df["FVT"] = df["FVT"].astype(str)

    # Columna de falla: 1 si Status = 'FAILED'
    df["Fail"] = (
        df["Status"]
        .astype(str)
        .str.strip()
        .str.upper()
        .eq("FAILED")
        .astype(int)
    )

    # Semana (inicio de cada semana)
    df["Week"] = df["Date"].dt.to_period("W").dt.start_time

    return df


# --------- CARGA DEL RESUMEN DE LÍMITES (GETANGLE) ---------
@st.cache_data
def load_getangle_summary(path: str):
    df = pd.read_csv(path)

    # Asegurar tipos correctos
    df["FVT"] = df["FVT"].astype(str)
    df["BaseType"] = df["BaseType"].astype(str)
    df["Percent_out_of_limits"] = df["Percent_out_of_limits"].astype(float)

    return df


# --------- CONFIGURACIÓN DE LA PÁGINA ---------
st.set_page_config(
    page_title="Dashboard Maytag Series 6 – Xtronic",
    layout="wide",
)

st.title("Dashboard Maytag Series 6 – Xtronic")

# --------- RUTAS DE ARCHIVOS ---------
DATA_PATH = "maytag_dashboardFinal_data.csv"
SUMMARY_PATH = "getangle_summary_v2.csv"   # ←← NOMBRE ACTUALIZADO

data = load_data(DATA_PATH)
getangle_summary = load_getangle_summary(SUMMARY_PATH)

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
cw_rate = float(cw_rate.iloc[0]) if not cw_rate.empty else None

# --------- SIDEBAR: FILTROS ---------
st.sidebar.header("Filtros principales")

product_type = st.sidebar.radio(
    "Selecciona el tipo de producto",
    sorted(data["BaseType"].unique()),
    help="CD = secadoras, CW = lavadoras",
)

subset = data[data["BaseType"] == product_type].copy()

fvt_selected = st.sidebar.multiselect(
    "Selecciona FVT",
    sorted(subset["FVT"].unique()),
    default=sorted(subset["FVT"].unique()),
)

if fvt_selected:
    subset = subset[subset["FVT"].isin(fvt_selected)]

# --------- MÉTRICA PRINCIPAL DEL PRODUCTO SELECCIONADO ---------
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
        txt = "Sin datos suficientes."
    st.markdown(txt)

st.markdown("---")

# --------- DISTRIBUCIÓN POR FVT Y TENDENCIA SEMANAL ---------
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
        )
        fig_fvt.update_traces(
            texttemplate='%{text:.2f}%',
            textposition='outside'
        )
        fig_fvt.update_layout(
            yaxis_title="% de fallas",
            height=380,
            margin=dict(l=20, r=20, t=40, b=60),
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
        )
        fig_time.update_layout(
            yaxis_title="% de fallas",
            height=380,
            margin=dict(l=20, r=20, t=40, b=60),
        )
        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No hay datos con fecha para los filtros seleccionados.")

# ============================================================
#   NUEVA SECCIÓN: LÍMITES DE CONTROL (GETANGLE)
# ============================================================
st.markdown("---")
st.header("Análisis de límites de control – Pruebas GetAngle")

# Filtros para esta sección
col_filters1, col_filters2 = st.columns(2)

with col_filters1:
    base_for_limits = st.selectbox(
        "Tipo de producto (CD / CW)",
        sorted(getangle_summary["BaseType"].unique())
    )

with col_filters2:
    available_fvts = sorted(
        getangle_summary[getangle_summary["BaseType"] == base_for_limits]["FVT"].unique()
    )
    fvt_for_limits = st.selectbox(
        "Selecciona FVT para análisis de GetAngle",
        available_fvts,
    )

summary_filtered = getangle_summary[
    (getangle_summary["BaseType"] == base_for_limits) &
    (getangle_summary["FVT"] == fvt_for_limits)
]

if summary_filtered.empty:
    st.warning("No hay datos de límites para esta combinación de FVT y tipo de producto.")
else:
    st.markdown(
        f"**% de lecturas fuera de límites de control** "
        f"para las pruebas GetAngle de **{fvt_for_limits} – {base_for_limits}**."
    )

    fig_limits = px.bar(
        summary_filtered,
        x="Test",
        y="Percent_out_of_limits",
        text="Percent_out_of_limits",
        labels={"Test": "Prueba GetAngle", "Percent_out_of_limits": "% fuera de límites"},
    )

    fig_limits.update_traces(
        texttemplate='%{text:.1%}',
        textposition='outside'
    )
    fig_limits.update_layout(
        yaxis_tickformat=".0%",
        yaxis_title="% fuera de límites",
        xaxis_title="Prueba GetAngle",
        xaxis_tickangle=-45,
        height=450,
        margin=dict(l=40, r=30, t=40, b=120),
    )

    st.plotly_chart(fig_limits, use_container_width=True)


