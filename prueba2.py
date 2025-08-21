# Streamlit app adaptada desde "preg2 (6).py"
# Autor: Conversión a Streamlit por ChatGPT
# Ejecuta:  streamlit run app_preg2.py

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO

st.set_page_config(page_title="COVID-19 Viz – Pregunta 2", layout="wide")

GITHUB_BASE = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports"

@st.cache_data(show_spinner=False)
def load_daily_report(yyyy_mm_dd: str):
    yyyy, mm, dd = yyyy_mm_dd.split("-")
    url = f"{GITHUB_BASE}/{mm}-{dd}-{yyyy}.csv"
    df = pd.read_csv(url)
    # normalizar nombres por si varían
    lower = {c.lower(): c for c in df.columns}
    cols = {
        "country": lower.get("country_region", "Country_Region"),
        "province": lower.get("province_state", "Province_State"),
        "confirmed": lower.get("confirmed", "Confirmed"),
        "deaths": lower.get("deaths", "Deaths"),
        "recovered": lower.get("recovered", "Recovered") if "recovered" in lower else None,
        "active": lower.get("active", "Active") if "active" in lower else None,
    }
    return df, url, cols

st.sidebar.title("Opciones")
fecha = st.sidebar.date_input("Fecha del reporte (JHU CSSE)", value=pd.to_datetime("2022-09-09"))
fecha_str = pd.to_datetime(fecha).strftime("%Y-%m-%d")
df, source_url, cols = load_daily_report(fecha_str)
st.sidebar.caption(f"Fuente: {source_url}")

st.title("Exploración COVID-19 – Versión Streamlit (Preg2)")
st.caption("Adaptación fiel del script original: mostrar/ocultar filas/columnas y varios gráficos (líneas, barras, sectores, histograma y boxplot).")

# ———————————————————————————————————————————————
# a) Mostrar todas las filas del dataset, luego volver al estado inicial
#    (en UI lo hacemos con un checkbox)
# ———————————————————————————————————————————————
st.header("a) Mostrar filas")
mostrar_todas = st.checkbox("Mostrar todas las filas", value=False)
if mostrar_todas:
    st.dataframe(df, use_container_width=True)
else:
    st.dataframe(df.head(25), use_container_width=True)

# ———————————————————————————————————————————————
# b) Mostrar todas las columnas del dataset; volver al estado inicial
#    (checkbox que expande/contrae columnas)
# ———————————————————————————————————————————————
st.header("b) Mostrar columnas")
with st.expander("Vista de columnas"):
    st.write(list(df.columns))

st.caption("Usa el scroll horizontal de la tabla para ver todas las columnas en pantalla.")

# ———————————————————————————————————————————————
# c) Línea del total de fallecidos (>2500) vs Confirmed/Recovered/Active por país
#    Reproducimos la lógica: filtrar por muertes>2500, agrupar por país y graficar.
# ———————————————————————————————————————————————
st.header("c) Gráfica de líneas por país (muertes > 2500)")
C, D = cols["confirmed"], cols["deaths"]
R, A = cols["recovered"], cols["active"]

metrics = [m for m in [C, D, R, A] if m and m in df.columns]
base = df[[cols["country"]] + metrics].copy()
base = base.rename(columns={cols["country"]: "Country_Region"})

filtrado = base.loc[base[D] > 2500]
agr = filtrado.groupby("Country_Region").sum(numeric_only=True)
orden = agr.sort_values(D)

# Opción 1: gráfico estilo original (x=Deaths; y=Confirm/Recovered/Active)
fig1, ax1 = plt.subplots()
if D in orden.columns:
    x = orden[D].tolist()
    if C in orden.columns:
        ax1.plot(x, orden[C].tolist(), label="Confirmed")
    if R and R in orden.columns:
        ax1.plot(x, orden[R].tolist(), label="Recovered")
    if A and A in orden.columns:
        ax1.plot(x, orden[A].tolist(), label="Active")
    ax1.set_title("Relación con muertes (>2500)")
    ax1.set_xlabel("Deaths")
    ax1.grid(True)
    ax1.legend()
st.pyplot(fig1, use_container_width=True)

# Opción 2: líneas por país con índice categórico (puede ser denso)
with st.expander("Ver líneas por país (índice categórico)"):
    fig2, ax2 = plt.subplots()
    sel = orden.head(30)  # limitar para que sea legible
    for col in [c for c in [C, R, A] if c in sel.columns]:
        ax2.plot(range(len(sel)), sel[col].values, marker="o", label=col)
    ax2.set_xticks(range(len(sel)))
    ax2.set_xticklabels(sel.index, rotation=90)
    ax2.set_title("Top 30 países por muertes (>2500) – líneas por métrica")
    ax2.grid(True)
    ax2.legend()
    st.pyplot(fig2, use_container_width=True)

# ———————————————————————————————————————————————
# d) Barras de fallecidos de estados de Estados Unidos
# ———————————————————————————————————————————————
st.header("d) Barras: fallecidos por estado de EE.UU.")
country_col = cols["country"]
prov_col = cols["province"]

dfu = df[df[country_col] == "US"]
if len(dfu) == 0:
    st.info("Para esta fecha no hay registros con Country_Region='US'.")
else:
    agg_us = dfu.groupby(prov_col)[D].sum(numeric_only=True).sort_values(ascending=False)
    top_n = st.slider("Top estados por fallecidos", 5, 50, 20)
    fig3, ax3 = plt.subplots()
    agg_us.head(top_n).plot(kind="bar", ax=ax3)
    ax3.set_ylabel("Fallecidos")
    ax3.set_title("Estados de EE.UU. – Total de fallecidos")
    st.pyplot(fig3, use_container_width=True)

# ———————————————————————————————————————————————
# e) Pie: fallecidos de Colombia, Chile, Perú, Argentina y México
# ———————————————————————————————————————————————
st.header("e) Gráfica de sectores (pie)")
lista_paises = ["Colombia", "Chile", "Peru", "Argentina", "Mexico"]
sel = st.multiselect("Países", sorted(df[country_col].unique().tolist()), default=lista_paises)
agg_latam = df[df[country_col].isin(sel)].groupby(country_col)[D].sum(numeric_only=True)
fig4, ax4 = plt.subplots()
if agg_latam.sum() > 0:
    ax4.pie(agg_latam.values, labels=agg_latam.index, autopct="%0.1f %%")
    ax4.set_title("Participación de fallecidos")
else:
    ax4.text(0.5, 0.5, "Sin datos para los países seleccionados", ha="center")
st.pyplot(fig4, use_container_width=True)

# ———————————————————————————————————————————————
# f) Histograma del total de fallecidos por país
# ———————————————————————————————————————————————
st.header("f) Histograma de fallecidos por país")
muertes_pais = df.groupby(country_col)[D].sum(numeric_only=True)
fig5, ax5 = plt.subplots()
ax5.hist(muertes_pais.values, bins=20, edgecolor="black")
ax5.set_xlabel("Fallecidos (suma por país)")
ax5.set_ylabel("Frecuencia")
ax5.set_title("Histograma")
st.pyplot(fig5, use_container_width=True)

# ———————————————————————————————————————————————
# g) Boxplot de Confirmed, Deaths, Recovered, Active
# ———————————————————————————————————————————————
st.header("g) Boxplot")
cols_box = [c for c in [C, D, R, A] if c and c in df.columns]
subset = df[cols_box].fillna(0)
# limitar para que sea legible como en el script (25 filas)
subset_plot = subset.head(25)
fig6, ax6 = plt.subplots()
ax6.boxplot([subset_plot[c].tolist() for c in cols_box])
ax6.set_xticklabels(cols_box)
ax6.set_title("Boxplot – primeras 25 filas")
st.pyplot(fig6, use_container_width=True)

# ———————————————————————————————————————————————
# Extra: info del DataFrame (texto, como hacía el script con prints)
# ———————————————————————————————————————————————
with st.expander("Información del DataFrame (df.info)"):
    buf = StringIO()
    df.info(buf=buf)
    st.code(buf.getvalue())
