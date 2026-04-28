import streamlit as st
import pandas as pd
import requests
from datetime import date
import calendar
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Font
from openpyxl.utils import get_column_letter

# =================================
# Configuración general
# =================================
st.set_page_config(
    page_title="Control de gastos",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("💰 Control de gastos")

API_URL = "https://control-gastos-backend-4s5z.onrender.com/"

# =================================
# Categorías (UX core)
# =================================
CATEGORIAS = {
    "🚗 Transporte": [
        "Combustible", "Transporte público", "Estacionamiento",
        "Peajes", "Mantenimiento auto", "Seguro auto"
    ],
    "🏠 Hogar": [
        "Alquiler", "Luz", "Gas", "Agua",
        "Internet", "Expensas", "Impuestos"
    ],
    "🍕 Comida": [
        "Supermercado", "Comidas fuera", "Delivery"
    ],
    "💊 Salud": [
        "Farmacia", "Prepaga", "Consultas médicas"
    ],
    "📱 Servicios": [
        "Celular", "Streaming", "Otros servicios"
    ],
    "🛍️ Gustos": [
        "Ropa", "Salidas", "Viajes", "Regalos", "Otros"
    ],
    "💰 Ingresos": [
        "Sueldo", "Freelance", "Extras", "Otros ingresos"
    ]
}

# =================================
# Backend helpers
# =================================
def cargar_datos():
    r = requests.get(f"{API_URL}/movimientos")
    if r.status_code == 200:
        df = pd.DataFrame(r.json())
        if not df.empty:
            df.rename(columns={
                "fecha": "Fecha",
                "monto": "Monto",
                "tipo": "Tipo",
                "categoria": "Categoría",
                "descripcion": "Descripción"
            }, inplace=True)
            df["Fecha"] = pd.to_datetime(df["Fecha"])
        return df
    st.error("No se pudieron cargar los datos")
    return pd.DataFrame()

# =================================
# ➕ Alta de movimiento
# =================================
with st.container():
    st.subheader("➕ Agregar movimiento")

    col1, col2, col3 = st.columns(3)

    with col1:
        fecha = st.date_input(
            "📅 Fecha",
            value=date.today(),
            format="DD/MM/YYYY",
            key="alta_fecha"
        )

    with col2:
        monto = st.number_input(
            "💵 Monto",
            min_value=0.0,
            step=100.0,
            key="alta_monto"
        )

    with col3:
        tipo = st.selectbox(
            "Tipo",
            ["Gasto", "Ingreso"],
            key="alta_tipo"
        )

    col4, col5 = st.columns(2)

    with col4:
        grupo = st.selectbox(
            "Grupo",
            list(CATEGORIAS.keys()),
            key="alta_grupo"
        )

    with col5:
        subcategoria = st.selectbox(
            "Categoría",
            CATEGORIAS[grupo],
            key="alta_categoria"
        )

    descripcion = st.text_input(
        "📝 Descripción (opcional)",
        key="alta_desc"
    )

    if st.button("✅ Guardar movimiento"):
        categoria_final = f"{grupo} › {subcategoria}"

        payload = {
            "fecha": str(fecha),
            "monto": float(monto),
            "tipo": tipo,
            "categoria": categoria_final,
            "descripcion": descripcion
        }

        r = requests.post(f"{API_URL}/movimientos", json=payload)
        if r.status_code == 200:
            st.success("Movimiento guardado ✅")
            st.rerun()
        else:
            st.error("Error al guardar el movimiento")

# =================================
# 📅 Calendario y resumen
# =================================
datos = cargar_datos()

st.divider()
st.subheader("📅 Resumen mensual")

if not datos.empty:

    col1, col2 = st.columns(2)
    with col1:
        mes = st.selectbox(
            "Mes",
            range(1, 13),
            index=date.today().month - 1
        )
    with col2:
        anio = st.selectbox(
            "Año",
            sorted(datos["Fecha"].dt.year.unique(), reverse=True)
        )

    datos_mes = datos[
        (datos["Fecha"].dt.month == mes) &
        (datos["Fecha"].dt.year == anio)
    ]

    total_ingresos = datos_mes[datos_mes["Tipo"] == "Ingreso"]["Monto"].sum()
    total_gastos = datos_mes[datos_mes["Tipo"] == "Gasto"]["Monto"].sum()
    balance = total_ingresos - total_gastos

    c1, c2, c3 = st.columns(3)
    c1.metric("🟢 Ingresos", f"${total_ingresos:,.0f}")
    c2.metric("🔴 Gastos", f"${total_gastos:,.0f}")
    c3.metric("⚖️ Balance", f"${balance:,.0f}")

    # =================================
    # Resumen diario
    # =================================
    resumen = datos_mes.copy()
    resumen["Ingreso"] = resumen.apply(
        lambda x: x["Monto"] if x["Tipo"] == "Ingreso" else 0, axis=1
    )
    resumen["Gasto"] = resumen.apply(
        lambda x: x["Monto"] if x["Tipo"] == "Gasto" else 0, axis=1
    )

    diario = resumen.groupby(
        resumen["Fecha"].dt.day
    )[["Ingreso", "Gasto"]].sum()

    # =================================
    # Calendario visual
    # =================================
    cal = calendar.monthcalendar(anio, mes)
    filas = []

    for semana in cal:
        fila = []
        for dia in semana:
            if dia == 0:
                fila.append("")
            elif dia in diario.index:
                fila.append(
                    f"{dia}\n"
                    f"- {diario.loc[dia,'Gasto']:.0f}\n"
                    f"+ {diario.loc[dia,'Ingreso']:.0f}"
                )
            else:
                fila.append(str(dia))
        filas.append(fila)

    cal_df = pd.DataFrame(
        filas,
        columns=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    )

    st.dataframe(cal_df, use_container_width=True)

    # =================================
    # 📋 Detalle por día (friendly)
    # =================================
    st.subheader("📋 Detalle por día")

    if not diario.empty:
        dia = st.selectbox("Seleccioná un día", sorted(diario.index))

        detalle = datos_mes[datos_mes["Fecha"].dt.day == dia].copy()
        detalle["Fecha"] = detalle["Fecha"].dt.strftime("%d/%m/%Y")

        st.dataframe(detalle, use_container_width=True)

        st.caption(
            f"Este día gastaste en promedio "
            f"${detalle[detalle['Tipo']=='Gasto']['Monto'].sum():,.0f}"
        )

else:
    st.info("Todavía no hay datos para mostrar")