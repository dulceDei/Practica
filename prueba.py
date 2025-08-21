# app.py
# Streamlit COVID-19 explorer
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.set_page_config(page_title="COVID-19 Explorer", layout="wide")

# ---------- Parámetros ----------
GITHUB_BASE = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_daily_reports"

# ---------- Utilidades ----------
@st.cache_data(show_spinner=False)
def load_daily_report(yyyy_mm_dd: str) -> pd.DataFrame:
    """Descarga y lee el CSV del repositorio de JHU para una fecha (MM-DD-YYYY)."""
    # yyyy_mm_dd = "2022-09-09" -> "09-09-2022"
    yyyy, mm, dd = yyyy_mm_dd.split("-")
    url = f"{GITHUB_BASE}/{mm}-{dd}-{yyyy}.csv"
    df = pd.read_csv(url)
    # Normalizar nombres esperados
    cols = {c.lower(): c for c in df.columns}
    # Columnas típicas
    want = {
        "country_region": None, "province_state": None,
        "confirmed": None, "deaths": None, "recovered": None, "active": None,
        "admin2": None, "fips": None
    }
    for k in list(want):
        # coincide por lower
        if k in cols:
            want[k] = cols[k]
    return df, url, want

def safe_sum(df: pd.DataFrame, cols):
    cols = [c for c in cols if c in df.columns]
    return df.groupby("Country_Region", dropna=False)[cols].sum().sort_values(by=cols[0], ascending=False)

def df_to_excel_bytes(df: pd.DataFrame, sheet="hoja1") -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)
    return bio.getvalue()

# ---------- Sidebar ----------
st.sidebar.title("Opciones")
date = st.sidebar.date_input("Fecha del reporte (JHU CSSE)", value=pd.to_datetime("2022-09-09"))
date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
df, source_url, want = load_daily_report(date_str)
st.sidebar.caption(f"Fuente: {source_url}")

# ---------- Encabezado ----------
st.title("COVID-19 Explorer (JHU Daily Reports)")
st.caption("Adaptación a Streamlit del script con agrupaciones, top-N y exportación a Excel.")

# ---------- Sección A: vista general + faltantes ----------
st.header("A) Exploración general y valores faltantes")
c1, c2 = st.columns(2)
with c1:
    st.subheader("Primeras 10 filas")
    st.dataframe(df.head(10), use_container_width=True)
with c2:
    st.subheader("Últimas 10 filas")
    st.dataframe(df.tail(10), use_container_width=True)

with st.expander("Información del dataset"):
    buf = BytesIO()
    df.info(buf=buf)
    st.code(buf.getvalue().decode())

with st.expander("Conteo de faltantes por columna"):
    st.write(df.isna().sum())

# ---------- Sección B: por país ----------
st.header("B) Casos por país")
# columnas disponibles
confirmed = want["confirmed"] or "Confirmed"
deaths    = want["deaths"] or "Deaths"
recovered = want["recovered"] or ("Recovered" if "Recovered" in df.columns else None)
active    = want["active"] or ("Active" if "Active" in df.columns else None)

cols_sum = [c for c in [confirmed, deaths, recovered, active] if c in df.columns]
by_country = df.groupby("Country_Region", dropna=False)[cols_sum].sum().sort_values(by=cols_sum[0], ascending=False)
st.dataframe(by_country, use_container_width=True)

c3, c4 = st.columns(2)
with c3:
    n_top = st.slider("Top N por confirmados", 5, 30, 10)
    st.subheader("Top países por confirmados")
    st.bar_chart(by_country[confirmed].head(n_top))
with c4:
    st.subheader("Top países por fallecidos")
    st.bar_chart(by_country[deaths].head(n_top))

# ---------- Sección C: por país y provincia ----------
st.header("C) Casos por país y provincia/estado")
country_sel = st.selectbox("Elige un país para detallar por provincia/estado", sorted(df["Country_Region"].dropna().unique().tolist()))
prov_cols = [c for c in [confirmed, deaths, recovered] if c in df.columns]
g_country_prov = (
    df[df["Country_Region"] == country_sel]
    .groupby(["Country_Region", "Province_State"], dropna=False)[prov_cols]
    .sum()
    .reset_index()
    .sort_values(by=prov_cols[0], ascending=False)
)
st.dataframe(g_country_prov, use_container_width=True)

# ---------- Sección D: ejemplo de orden por confirmados (como China/Perú en el script) ----------
st.header("D) Provincias/estados ordenados por confirmados (del país seleccionado)")
st.dataframe(g_country_prov.sort_values(by=prov_cols[0], ascending=False), use_container_width=True)

# ---------- Sección E & F: Top 10 confirmados / fallecidos y extremos ----------
st.header("E) y F) Top 10 por confirmados y por fallecidos, además de mayor/menor fallecidos")
top_confirmed = by_country[[confirmed]].head(10)
top_deaths = by_country[[deaths]].head(10)
c5, c6 = st.columns(2)
with c5:
    st.subheader("Top 10 - Confirmados")
    st.dataframe(top_confirmed)
with c6:
    st.subheader("Top 10 - Fallecidos")
    st.dataframe(top_deaths)

max_deaths_country = by_country[by_country[deaths] == by_country[deaths].max()][[deaths]]
min_deaths_country = by_country[by_country[deaths] == by_country[deaths].min()][[deaths]]
st.markdown(f"**Mayor número de fallecidos:**")
st.dataframe(max_deaths_country)
st.markdown(f"**Menor número de fallecidos:**")
st.dataframe(min_deaths_country)

# ---------- Sección G: muestreo aleatorio y eliminación de columnas ----------
st.header("G) Muestreo aleatorio de 50 filas y eliminación de columnas por índice")
st.caption("En el script original se pedían 50 filas aleatorias y borrar columnas 0,1,5,6,11. Aquí puedes ajustar.")
n_rows = st.number_input("Tamaño de la muestra aleatoria", 10, min(50, len(df)), 50, step=5)
sample_df = df.sample(n=min(n_rows, len(df)), random_state=42).reset_index(drop=True)

default_indices = [0, 1, 5, 6, 11]
indices_text = st.text_input("Índices de columnas a eliminar (separados por coma)", ",".join(map(str, default_indices)))
try:
    idx_to_drop = sorted({int(x.strip()) for x in indices_text.split(",") if x.strip().isdigit()})
except Exception:
    idx_to_drop = default_indices

cols_to_drop = [df.columns[i] for i in idx_to_drop if i < len(df.columns)]
df_g = sample_df.drop(columns=cols_to_drop, errors="ignore")
st.subheader("Muestra procesada")
st.dataframe(df_g, use_container_width=True)

# ---------- Guardar a Excel y descargar ----------
st.subheader("Descargar la muestra en Excel")
excel_bytes = df_to_excel_bytes(df_g, sheet="hoja1")
st.download_button("Descargar Excel", data=excel_bytes, file_name="muestra.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------- Notas ----------
with st.expander("Notas técnicas"):
    st.markdown(
        """
- Los datos provienen del repositorio público **JHU CSSE** (archivos diarios).
- Algunas fechas no incluyen la columna `Recovered` o `Active`; la app se adapta.
- La exportación a Excel usa `openpyxl`. En despliegue, añade `openpyxl` a `requirements.txt`.
- La lógica reproduce lo que hacía tu script: head/tail, faltantes, agrupaciones, top-N,
  extremos por fallecidos, muestreo aleatorio y exportación.
"""
    )
