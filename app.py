import streamlit as st
import pandas as pd
import requests
from datetime import date
import calendar
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Alignment, Font
from openpyxl.utils import get_column_letter

# =====================
# Configuración
# =====================
st.set_page_config(page_title="Control de gastos", layout="wide")
st.title("💰 Control de gastos")

API_URL = "https://control-gastos-backend-4s5z.onrender.com"

# =====================
# Categorías UX
# =====================
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

# =====================
# Backend helpers
# =====================
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
    return pd.DataFrame()

datos = cargar_datos()

# =====================
# Tabs
# =====================
tab_mes, tab_hist = st.tabs(["📅 Mes actual", "📊 Histórico"])

# ==========================================================
# TAB 1 — MES ACTUAL
# ==========================================================
with tab_mes:

    # -------- Alta --------
    with st.container():
        st.header("➕ Agregar movimiento")

        c1, c2, c3 = st.columns(3)
        with c1:
            fecha = st.date_input(
                "📅 Fecha",
                value=date.today(),
                format="DD/MM/YYYY",
                key="alta_fecha"
            )

        with c2:
            monto = st.number_input(
                "💵 Monto",
                min_value=0.0,
                step=100.0,
                key="alta_monto"
            )

        with c3:
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"], key="alta_tipo")

        c4, c5 = st.columns(2)
        with c4:
            grupo = st.selectbox("Grupo", list(CATEGORIAS.keys()), key="alta_grupo")
        with c5:
            subcategoria = st.selectbox("Categoría", CATEGORIAS[grupo], key="alta_categoria")

        descripcion = st.text_input("📝 Descripción", key="alta_desc")

        if st.button("✅ Guardar movimiento"):
            categoria_final = f"{grupo} › {subcategoria}"
            payload = {
                "fecha": str(fecha),
                "monto": float(monto),
                "tipo": tipo,
                "categoria": categoria_final,
                "descripcion": descripcion
            }
            requests.post(f"{API_URL}/movimientos", json=payload)
            st.success("Movimiento guardado ✅")
            st.rerun()

    # -------- Calendario --------
    if not datos.empty:
        st.header("📅 Calendario mensual")

        mes = st.selectbox("Mes", range(1, 13), index=date.today().month - 1)
        anio = st.selectbox("Año", sorted(datos["Fecha"].dt.year.unique(), reverse=True))

        datos_mes = datos[
            (datos["Fecha"].dt.month == mes) &
            (datos["Fecha"].dt.year == anio)
        ]

        total_ing = datos_mes[datos_mes["Tipo"] == "Ingreso"]["Monto"].sum()
        total_gas = datos_mes[datos_mes["Tipo"] == "Gasto"]["Monto"].sum()
        bal = total_ing - total_gas

        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 Ingresos", f"${total_ing:,.0f}")
        c2.metric("🔴 Gastos", f"${total_gas:,.0f}")
        c3.metric("⚖️ Balance", f"${bal:,.0f}")

        resumen = datos_mes.copy()
        resumen["Ingreso"] = resumen.apply(lambda x: x["Monto"] if x["Tipo"] == "Ingreso" else 0, axis=1)
        resumen["Gasto"] = resumen.apply(lambda x: x["Monto"] if x["Tipo"] == "Gasto" else 0, axis=1)

        diario = resumen.groupby(resumen["Fecha"].dt.day)[["Ingreso", "Gasto"]].sum()

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

        st.dataframe(
            pd.DataFrame(filas, columns=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]),
            use_container_width=True
        )

        # -------- Detalle / Editar / Borrar --------
        st.header("📋 Detalle por día")

        if not diario.empty:
            dia_sel = st.selectbox("Día", sorted(diario.index))
            detalle = datos_mes[datos_mes["Fecha"].dt.day == dia_sel]
            detalle_vis = detalle.copy()
            detalle_vis["Fecha"] = detalle_vis["Fecha"].dt.strftime("%d/%m/%Y")
            st.dataframe(detalle_vis, use_container_width=True)

            mov_ids = detalle.index.tolist()
            mov_idx = st.selectbox(
                "Movimiento",
                mov_ids,
                format_func=lambda i: f"{detalle.loc[i,'Tipo']} ${detalle.loc[i,'Monto']}"
            )
            mov = detalle.loc[mov_idx]

            st.subheader("✏️ Editar / 🗑️ Borrar")

            ef = st.date_input(
                "Fecha",
                mov["Fecha"].date(),
                format="DD/MM/YYYY",
                key=f"edit_fecha_{mov['id']}"
            )
            em = st.number_input("Monto", value=float(mov["Monto"]), key=f"edit_monto_{mov['id']}")
            et = st.selectbox(
                "Tipo",
                ["Gasto", "Ingreso"],
                index=0 if mov["Tipo"] == "Gasto" else 1,
                key=f"edit_tipo_{mov['id']}"
            )
            ec = st.text_input("Categoría", mov["Categoría"], key=f"edit_categoria_{mov['id']}")
            ed = st.text_input("Descripción", mov["Descripción"], key=f"edit_desc_{mov['id']}")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Guardar cambios"):
                    payload = {
                        "fecha": str(ef),
                        "monto": em,
                        "tipo": et,
                        "categoria": ec,
                        "descripcion": ed
                    }
                    requests.put(f"{API_URL}/movimientos/{mov['id']}", json=payload)
                    st.rerun()

            with c2:
                if st.button("🗑️ Borrar movimiento"):
                    requests.delete(f"{API_URL}/movimientos/{mov['id']}")
                    st.rerun()

# ==========================================================
# TAB 2 — HISTÓRICO
# ==========================================================
with tab_hist:
    st.header("📊 Histórico de movimientos")

    if datos.empty:
        st.info("No hay datos históricos todavía")
    else:
        col1, col2 = st.columns(2)

        with col1:
            anio_hist = st.selectbox(
                "Año",
                sorted(datos["Fecha"].dt.year.unique(), reverse=True)
            )

        with col2:
            meses_disp = sorted(
                datos[datos["Fecha"].dt.year == anio_hist]["Fecha"].dt.month.unique()
            )
            mes_hist = st.selectbox("Mes", ["Todos"] + meses_disp)

        datos_hist = datos[datos["Fecha"].dt.year == anio_hist]
        if mes_hist != "Todos":
            datos_hist = datos_hist[datos_hist["Fecha"].dt.month == mes_hist]

        datos_hist_vis = datos_hist.copy()
        datos_hist_vis["Fecha"] = datos_hist_vis["Fecha"].dt.strftime("%d/%m/%Y")

        st.dataframe(
            datos_hist_vis.sort_values("Fecha"),
            use_container_width=True
        )

        ti = datos_hist[datos_hist["Tipo"] == "Ingreso"]["Monto"].sum()
        tg = datos_hist[datos_hist["Tipo"] == "Gasto"]["Monto"].sum()

        c1, c2, c3 = st.columns(3)
        c1.metric("🟢 Ingresos", f"${ti:,.0f}")
        c2.metric("🔴 Gastos", f"${tg:,.0f}")
        c3.metric("⚖️ Balance", f"${ti - tg:,.0f}")
