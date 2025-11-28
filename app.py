import streamlit as st
import pandas as pd
import plotly.express as px

# =========================================================
#              CARGA BASE PRINCIPAL
# =========================================================
@st.cache_data
def load_data(path: str):
    df = pd.read_csv(path, parse_dates=["Date"])

    df["BaseType"] = df["BaseType"].astype(str)
    df["FVT"] = df["FVT"].astype(str)

    df["Fail"] = (
        df["Status"].astype(str).str.strip().str.upper().eq("FAILED").astype(int)
    )

    df["Week"] = df["Date"].dt.to_period("W").dt.start_time
    return df


# =========================================================
#          CARGA RESUMEN LÍMITES GETANGLE
# =========================================================
@st.cache_data
def load_getangle_summary(path: str):
    df = pd.read_csv(path)

    df["FVT"] = df["FVT"].astype(str)
    df["BaseType"] = df["BaseType"].astype(str)

    if "Test_label" in df.columns:
        df["Test_label"] = df["Test_label"].astype(str)
    if "Test_col_used" in df.columns:
        df["Test_col_used"] = df["Test_col_used"].astype(str)

    df["Percent_out_of_limits"] = df["Percent_out_of_limits"].astype(float)

    return df


# =========================================================
#        CONFIG PÁGINA
# =========================================================
st.set_page_config(
    page_title="Dashboard Maytag Series 6 – Xtronic",
    layout="wide",
)

st.title("Dashboard Maytag Series 6 – Xtronic")
st.markdown(
    """
Monitoreo de desempeño de pruebas CD (secadoras) y CW (lavadoras)  
• % de fallas por tipo de producto, por FVT y por semana  
• % de lecturas fuera de límites de control para pruebas GetAngle  
"""
)

# =========================================================
#         RUTAS DE ARCHIVOS
# =========================================================
DATA_PATH = "maytag_dashboardFinal_data.csv"
SUMMARY_PATH = "getangle_summary_v2.csv"

data = load_data(DATA_PATH)
getangle_summary = load_getangle_summary(SUMMARY_PATH)

# =========================================================
#            CALC. FALLOS CD vs CW
# =========================================================
failure_by_product = (
    data.groupby("BaseType")["Fail"].mean().reset_index(name="FailRate")
)
failure_by_product["FailRate_pct"] = 100 * failure_by_product["FailRate"]

cd_rate = failure_by_product.query("BaseType == 'CD'")["FailRate_pct"]
cw_rate = failure_by_product.query("BaseType == 'CW'")["FailRate_pct"]

cd_rate = float(cd_rate.iloc[0]) if not cd_rate.empty else None
cw_rate = float(cw_rate.iloc[0]) if not cw_rate.empty else None

# =========================================================
#                         FILTROS
# =========================================================
st.sidebar.header("Filtros principales")

product_type = st.sidebar.radio(
    "Selecciona el tipo de producto",
    sorted(data["BaseType"].unique()),
)

subset = data[data["BaseType"] == product_type].copy()

fvt_selected = st.sidebar.multiselect(
    "Selecciona FVT",
    sorted(subset["FVT"].unique()),
    default=sorted(subset["FVT"].unique()),
)

if fvt_selected:
    subset = subset[subset["FVT"].isin(fvt_selected)]

# =========================================================
#              MÉTRICA PRINCIPAL
# =========================================================
selected_fail_rate = subset["Fail"].mean() * 100 if len(subset) else 0

col_top1, col_top2 = st.columns([2, 1])

with col_top1:
    st.subheader(f"{product_type} – porcentaje de fallas")
    st.metric(
        label=f"% de fallas {product_type}",
        value=f"{selected_fail_rate:.2f} %",
    )

with col_top2:
    st.subheader("Comparativo general CD vs CW")

    if cd_rate is None and cw_rate is None:
        st.write("Sin datos.")
    else:
        st.markdown(
            f"""
            - **CD:** {cd_rate:.2f}%  
            - **CW:** {cw_rate:.2f}%  
            """
        )

st.markdown("---")

# =========================================================
#           GRAFICA 1 — FALLAS POR FVT (FORMATO PRO)
# =========================================================
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Porcentaje de fallas por FVT")

    failure_by_fvt = (
        subset.groupby("FVT")["Fail"].mean().reset_index(name="FailRate")
    )
    failure_by_fvt["FailRate_pct"] = 100 * failure_by_fvt["FailRate"]

    if not failure_by_fvt.empty:

        fig_fvt = px.bar(
            failure_by_fvt.sort_values("FailRate_pct", ascending=False),
            x="FVT",
            y="FailRate_pct",
            text="FailRate_pct",
            color_discrete_sequence=["steelblue"],
        )

        fig_fvt.update_traces(
            texttemplate='%{text:.2f}%',
            textposition="outside"
        )

        fig_fvt.update_layout(
            yaxis_title="% de fallas",
            height=420,
            yaxis_range=[0, 20],  
            margin=dict(l=20, r=20, t=40, b=80),
            showlegend=False,
        )

        st.plotly_chart(fig_fvt, use_container_width=True)

    else:
        st.info("No hay datos para los filtros seleccionados.")

# =========================================================
#      GRAFICA 2 — TENDENCIA SEMANAL
# =========================================================
with col2:
    st.markdown("### Tendencia de fallas por semana")

    failure_over_time = (
        subset.groupby("Week")["Fail"].mean().reset_index(name="FailRate")
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
            height=420,
            margin=dict(l=20, r=20, t=40, b=60),
        )

        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No hay datos con fecha para los filtros seleccionados.")

# =========================================================
#      SECCIÓN GETANGLE — VERSIÓN PROFESIONAL FINAL
# =========================================================
st.markdown("---")
st.header("Análisis de límites de control – Pruebas GetAngle")

available_fvts_limits = sorted(getangle_summary["FVT"].unique())

fvt_for_limits = st.selectbox(
    "Selecciona FVT para análisis de GetAngle",
    available_fvts_limits,
)

summary_filtered = getangle_summary[getangle_summary["FVT"] == fvt_for_limits]

if summary_filtered.empty:
    st.warning("No hay datos de límites para esta FVT.")
else:

    if "Test_label" in summary_filtered.columns:
        x_col = "Test_label"
    elif "Test_col_used" in summary_filtered.columns:
        x_col = "Test_col_used"
    else:
        x_col = "Test"

    summary_plot = summary_filtered.sort_values("Percent_out_of_limits", ascending=True)

    fig_limits = px.bar(
        summary_plot,
        y=x_col,
        x="Percent_out_of_limits",
        orientation="h",
        color_discrete_sequence=["royalblue"],
        text="Percent_out_of_limits",
        labels={
            x_col: "Prueba GetAngle",
            "Percent_out_of_limits": "% fuera de límites",
        },
    )

    fig_limits.update_traces(
        texttemplate="%{text:.2%}",  # SOLO AL FINAL
        textposition="outside",
        insidetextanchor=None,       # *** EVITA QUE APAREZCA TEXTO DENTRO ***
    )

    fig_limits.update_layout(
        xaxis_title="% fuera de límites",
        yaxis_title="Prueba GetAngle",
        height=550,
        margin=dict(l=40, r=20, t=40, b=60),
        xaxis_range=[0, summary_plot["Percent_out_of_limits"].max() * 1.3],  # NO barras gigantes
        showlegend=False,
    )

    st.plotly_chart(fig_limits, use_container_width=True)

