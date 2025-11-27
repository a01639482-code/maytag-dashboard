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
cw_rate = float(cw_rate.iloc[0]) if not cw_rate.empty else None

# --------- SIDEBAR: FILTROS ---------
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
        value=f"{selected_fail_rate:.1f} %",   # 1 decimal
    )

with col_top2:
    st.subheader("Comparativo general CD vs CW")
    txt = ""
    if cd_rate is not None and cw_rate is not None:
        txt = f"- CD: **{cd_rate:.1f}%**\n- CW: **{cw_rate:.1f}%**"
    elif cd_rate is not None:
        txt = f"- CD: **{cd_rate:.1f}%**"
    elif cw_rate is not None:
        txt = f"- CW: **{cw_rate:.1f}%**"
    st.markdown(txt)

st.markdown("---")

# --------- DISTRIBUCIÓN POR FVT Y TENDENCIA SEMANAL (2 CUADRANTES) ---------
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

        # ---- Estética de la gráfica por FVT ----
        max_rate_fvt = failure_by_fvt["FailRate_pct"].max()

fig_fvt.update_traces(
    marker_color=PRIMARY_COLOR,
    texttemplate="%{text:.1f}%",
    textposition="outside",
)

fig_fvt.update_layout(
    title_text="",          # <-- esto quita el 'undefined'
    showlegend=False,
    title_font=dict(size=22),
    xaxis_title="Modelo FVT",
    yaxis_title="% de fallas",
    yaxis_range=[0, max_rate_fvt * 1.15],  # deja espacio para el 18.9%
    bargap=0.2,
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

        # ---- Estética de la tendencia ----
        fig_time.update_traces(
            line_color=PRIMARY_COLOR,
            line_width=3,
            marker=dict(size=8),
        )
       max_rate_time = failure_over_time["FailRate_pct"].max()

fig_time.update_traces(
    line_color=PRIMARY_COLOR,
    line_width=3,
    marker=dict(size=8),
)

fig_time.update_layout(
    title_text="",          # <-- también quita el 'undefined' aquí
    showlegend=False,
    title_font=dict(size=22),
    xaxis_title="Semana",
    yaxis_title="% de fallas",
    yaxis_range=[0, max_rate_time * 1.15],
    height=380,
    margin=dict(l=20, r=20, t=40, b=40),
)

        st.plotly_chart(fig_time, use_container_width=True)
    else:
        st.info("No hay datos con fecha para los filtros seleccionados.")

