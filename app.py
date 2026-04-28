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
# Traer datos del backend
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
    return pd.DataFrame(columns=["Fecha", "Monto", "Tipo", "Categoría", "Descripción"])

datos = cargar_datos()

# =====================
# Formulario alta (MEJORADO)
# =====================
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
        r = requests.post(f"{API_URL}/movimientos", json=payload)
        if r.status_code == 200:
            st.success("Movimiento guardado ✅")
            st.rerun()

# =====================
# Calendario mensual
# =====================
st.header("📅 Calendario mensual")

if not datos.empty:

    mes = st.selectbox("Mes", range(1, 13), index=date.today().month - 1)
    anio = st.selectbox("Año", sorted(datos["Fecha"].dt.year.unique(), reverse=True))

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

    calendario_df = pd.DataFrame(
        filas, columns=["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    )
    st.dataframe(calendario_df, use_container_width=True)

    # =====================
    # Detalle / Editar / Borrar
    # =====================
    st.header("📋 Detalle por día")

    if not diario.empty:
        dia_sel = st.selectbox("Día", sorted(diario.index.tolist()))

        detalle_dia = datos_mes[datos_mes["Fecha"].dt.day == dia_sel]
        detalle_dia_vis = detalle_dia.copy()
        detalle_dia_vis["Fecha"] = detalle_dia_vis["Fecha"].dt.strftime("%d/%m/%Y")

        st.dataframe(detalle_dia_vis, use_container_width=True)

        mov_ids = detalle_dia.index.tolist()
        mov_idx = st.selectbox(
            "Movimiento",
            mov_ids,
            format_func=lambda i: f"{detalle_dia.loc[i,'Tipo']} ${detalle_dia.loc[i,'Monto']}"
        )

        mov = detalle_dia.loc[mov_idx]

        st.subheader("✏️ Editar / 🗑️ Borrar")

        ef = st.date_input(
            "Fecha",
            mov["Fecha"].date(),
            format="DD/MM/YYYY",
            key=f"edit_fecha_{mov['id']}"
        )
        em = st.number_input("Monto", value=float(mov["Monto"]), key=f"edit_monto_{mov['id']}")
        et = st.selectbox(
            "Tipo", ["Gasto", "Ingreso"],
            index=0 if mov["Tipo"]=="Gasto" else 1,
            key=f"edit_tipo_{mov['id']}"
        )
        ec = st.text_input(
            "Categoría",
            mov["Categoría"],
            key=f"edit_categoria_{mov['id']}"
        )
        ed = st.text_input(
            "Descripción",
            mov["Descripción"],
            key=f"edit_desc_{mov['id']}"
        )

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

    # =====================
    # Excel calendario (IGUAL QUE ANTES)
    # =====================
    st.header("📥 Descargar Excel")

    buffer = BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Calendario"

    colors = {
        "ingreso": PatternFill("solid", fgColor="C6EFCE"),
        "fijo": PatternFill("solid", fgColor="BDD7EE"),
        "variable": PatternFill("solid", fgColor="F8CBAD"),
        "head": PatternFill("solid", fgColor="D9D9D9")
    }

    headers = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
    for i,h in enumerate(headers,1):
        c = ws.cell(row=1,column=i,value=h)
        c.fill = colors["head"]
        c.font = Font(bold=True)
        ws.column_dimensions[get_column_letter(i)].width = 20

    gastos = datos_mes[datos_mes["Tipo"]=="Gasto"].groupby(datos_mes["Fecha"].dt.day)["Monto"].sum()
    ingresos = datos_mes[datos_mes["Tipo"]=="Ingreso"].groupby(datos_mes["Fecha"].dt.day)["Monto"].sum()

    fila = 2
    for semana in cal:
        for col,d in enumerate(semana,1):
            if d==0: continue
            c = ws.cell(row=fila,column=col,value=str(d))
            if d in ingresos:
                c.value += f"\n+ {ingresos[d]:.0f}"
                c.fill = colors["ingreso"]
            elif d in gastos:
                c.value += f"\n- {gastos[d]:.0f}"
                c.fill = colors["variable"]
            c.alignment = Alignment(wrap_text=True, vertical="top")
        fila += 1

    wb.save(buffer)

    st.download_button(
        "📅 Descargar calendario mensual en Excel",
        buffer.getvalue(),
        f"calendario_{anio}_{mes:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("No hay datos aún")