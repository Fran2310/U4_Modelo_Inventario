"""
==============================================================================
SISTEMA INTEGRAL DE GESTIÓN, SIMULACIÓN Y OPTIMIZACIÓN DE INVENTARIO
==============================================================================
Descripción:
    Script principal de la aplicación interactiva en Streamlit que unifica
    los 4 módulos del proyecto DCM-902:
        - Módulo 1: Core de inventario CRUD, costos estáticos, alertas y
                    gráfico resumen de existencias.
        - Módulo 2: Simulación discreta de eventos y políticas (s, Q) vs (R, S).
        - Módulo 3: Modelo continuo de degradación de perecederos (EDO).
        - Módulo 4: Experimentación, modelo EOQ, mapas de calor, Monte Carlo
                    y análisis de sensibilidad.

Ejecución:
    streamlit run main.py
==============================================================================
"""

from typing import Tuple
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from control_optimo import render_modulo_control_optimo
from modelo_continuo import render_modulo_continuo
from simulacion_discreta import render_modulo_simulacion_discreta


# ==============================================================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA (STREAMLIT)
# ==============================================================================
st.set_page_config(
    page_title="Simulador de Inventario | Supermercado",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Clave utilizada para almacenar el DataFrame en st.session_state
SESSION_KEY_INVENTARIO: str = "inventario_df"


# ==============================================================================
# GESTIÓN DE ESTADO (st.session_state)
# ==============================================================================
def inicializar_inventario() -> None:
    """
    Inicializa el DataFrame de inventario en st.session_state con 4 productos
    clave del supermercado y parámetros operativos si aún no ha sido creado.
    Calcula dinámicamente el Margen Unitario ($) = Precio Venta ($) - Costo Compra ($).
    """
    if SESSION_KEY_INVENTARIO not in st.session_state:
        datos_iniciales = {
            "Producto": ["Carne", "Lácteos", "Granos", "Higiene"],
            "Precio Venta ($)": [12.50, 4.80, 2.50, 6.20],
            "Costo Compra ($)": [8.20, 2.90, 1.20, 3.40],
            "Costo Almacenamiento ($/unidad)": [0.65, 0.30, 0.08, 0.15],
            "Stock Actual": [45, 85, 200, 110],
            "Stock Mínimo": [20, 30, 50, 35],
        }
        df = pd.DataFrame(datos_iniciales)
        df["Margen Unitario ($)"] = df["Precio Venta ($)"] - df["Costo Compra ($)"]

        columnas_ordenadas = [
            "Producto",
            "Precio Venta ($)",
            "Costo Compra ($)",
            "Margen Unitario ($)",
            "Costo Almacenamiento ($/unidad)",
            "Stock Actual",
            "Stock Mínimo",
        ]
        st.session_state[SESSION_KEY_INVENTARIO] = df[columnas_ordenadas]
    else:
        df = st.session_state[SESSION_KEY_INVENTARIO]
        if "Margen Unitario ($)" not in df.columns:
            df["Margen Unitario ($)"] = df["Precio Venta ($)"] - df["Costo Compra ($)"]
            st.session_state[SESSION_KEY_INVENTARIO] = df


def reiniciar_inventario() -> None:
    """Restaura los valores predeterminados del inventario en session_state."""
    if SESSION_KEY_INVENTARIO in st.session_state:
        del st.session_state[SESSION_KEY_INVENTARIO]
    inicializar_inventario()


# ==============================================================================
# CALCULADORA PURA DE COSTOS (MODELO FINANCIERO CON LUCRO CESANTE)
# ==============================================================================
def calcular_costos_estaticos(df: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Función pura que calcula y retorna los costos del inventario basándose
    en el estado actual de los datos.

    Fórmulas:
        1. Costo Total de Compra = Σ (Costo Compra ($) * Stock Actual)
        2. Costo Total de Almacenamiento = Σ (Costo Almacenamiento ($/unidad) * Stock Actual)
        3. Costo de Faltantes/Pérdidas (Lucro Cesante) =
           Σ (Margen Unitario ($) * Stock Mínimo) para productos con Stock Actual == 0.
    """
    costo_total_compra = float((df["Costo Compra ($)"] * df["Stock Actual"]).sum())
    costo_total_almacenamiento = float(
        (df["Costo Almacenamiento ($/unidad)"] * df["Stock Actual"]).sum()
    )
    productos_agotados = df["Stock Actual"] == 0
    lucro_cesante_serie = (
        df.loc[productos_agotados, "Margen Unitario ($)"]
        * df.loc[productos_agotados, "Stock Mínimo"]
    )
    costo_faltantes = float(lucro_cesante_serie.sum())

    return costo_total_compra, costo_total_almacenamiento, costo_faltantes


# ==============================================================================
# OPERACIONES DE INVENTARIO (LÓGICA CRUD)
# ==============================================================================
def agregar_stock(producto: str, cantidad: int) -> None:
    """Incrementa el stock actual de un producto en el DataFrame de session_state."""
    df = st.session_state[SESSION_KEY_INVENTARIO]
    idx = df[df["Producto"] == producto].index
    if not idx.empty:
        df.loc[idx, "Stock Actual"] += cantidad
        st.session_state[SESSION_KEY_INVENTARIO] = df
        st.toast(f"✅ Se agregaron {cantidad} unidades a **{producto}**.", icon="📥")


def retirar_stock(producto: str, cantidad: int) -> bool:
    """Disminuye el stock actual asegurando que no caiga por debajo de 0."""
    df = st.session_state[SESSION_KEY_INVENTARIO]
    idx = df[df["Producto"] == producto].index
    if not idx.empty:
        stock_disponible = int(df.loc[idx[0], "Stock Actual"])
        if cantidad > stock_disponible:
            return False
        df.loc[idx, "Stock Actual"] -= cantidad
        st.session_state[SESSION_KEY_INVENTARIO] = df
        st.toast(f"📉 Se retiraron {cantidad} unidades de **{producto}**.", icon="📤")
        return True
    return False


# ==============================================================================
# VISUALIZACIÓN RESUMEN DEL MÓDULO 1 (DASHBOARD)
# ==============================================================================
def graficar_estado_inventario(df: pd.DataFrame) -> go.Figure:
    """Gráfica de barras comparando Stock Actual vs. Stock Mínimo por producto."""
    colores = [
        "#d62728" if s == 0 else ("#ff9800" if s < m else "#2ca02c")
        for s, m in zip(df["Stock Actual"], df["Stock Mínimo"])
    ]
    fig = go.Figure(
        data=[
            go.Bar(
                name="Stock Actual",
                x=df["Producto"],
                y=df["Stock Actual"],
                marker_color=colores,
                text=df["Stock Actual"],
                textposition="auto",
            ),
            go.Bar(
                name="Stock Mínimo",
                x=df["Producto"],
                y=df["Stock Mínimo"],
                marker_color="rgba(100, 116, 139, 0.45)",
                text=df["Stock Mínimo"],
                textposition="auto",
            ),
        ]
    )
    fig.update_layout(
        title="📦 Nivel de Stock Actual vs. Stock Mínimo por Producto",
        xaxis_title="Producto",
        yaxis_title="Unidades",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=350,
    )
    return fig


def graficar_valor_comercial(df: pd.DataFrame) -> go.Figure:
    """Gráfica de composición del valor comercial del inventario por categoría."""
    valores = df["Precio Venta ($)"] * df["Stock Actual"]
    fig = go.Figure(
        data=[
            go.Pie(
                labels=df["Producto"],
                values=valores,
                hole=0.45,
                textinfo="label+percent",
                hovertemplate="%{label}<br>Valor Comercial: $%{value:,.2f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title="💵 Distribución del Valor Comercial en Almacén",
        height=350,
    )
    return fig


# ==============================================================================
# INICIALIZACIÓN Y BARRA LATERAL (CRUD GLOBAL)
# ==============================================================================
inicializar_inventario()

with st.sidebar:
    st.header("📦 Gestión de Inventario")
    st.caption("Entradas y Salidas Manuales de Mercancía")

    df_actual = st.session_state[SESSION_KEY_INVENTARIO]
    lista_productos = df_actual["Producto"].tolist()

    producto_seleccionado = st.selectbox(
        "Seleccionar Producto:",
        options=lista_productos,
        help="Elige el artículo sobre el cual registrar el movimiento.",
    )

    cantidad_movimiento = st.number_input(
        "Cantidad de Unidades:",
        min_value=1,
        value=10,
        step=1,
        help="Número de unidades a ingresar o retirar del almacén.",
    )

    col_btn_add, col_btn_sub = st.columns(2)
    with col_btn_add:
        if st.button("📥 Agregar", use_container_width=True, type="primary"):
            agregar_stock(producto_seleccionado, int(cantidad_movimiento))
            st.rerun()

    with col_btn_sub:
        if st.button("📤 Retirar", use_container_width=True):
            exito = retirar_stock(producto_seleccionado, int(cantidad_movimiento))
            if not exito:
                stock_actual_prod = df_actual.loc[
                    df_actual["Producto"] == producto_seleccionado, "Stock Actual"
                ].values[0]
                st.error(
                    f"⚠️ Operación rechazada: Stock insuficiente. "
                    f"Disponible: {stock_actual_prod} unidades."
                )
            else:
                st.rerun()

    st.divider()

    with st.expander("⚙️ Opciones del Sistema"):
        st.write("Restaura los valores base de inventario para pruebas y calibración.")
        if st.button("🔄 Reiniciar Inventario Base", use_container_width=True):
            reiniciar_inventario()
            st.rerun()

    st.caption(
        "Los cambios de stock realizados aquí se reflejan automáticamente "
        "en las pestañas de simulación y optimización."
    )


# ==============================================================================
# INTERFAZ PRINCIPAL INTEGRADA (4 MÓDULOS EN PESTAÑAS)
# ==============================================================================
st.title("🛒 Simulador Integral de Inventario — Supermercado")

df_inventario = st.session_state[SESSION_KEY_INVENTARIO]

tab_dashboard, tab_discreta, tab_continuo, tab_optimo = st.tabs(
    [
        "📊 Monitoreo Actual",
        "🎲 Simulación Discreta",
        "🧪 Modelo Continuo (EDO)",
        "🔬 Experimentación y Optimización",
    ]
)

# ------------------------------------------------------------------------------
# PESTAÑA 1: MÓDULO 1 — DASHBOARD CRUD Y COSTOS ESTÁTICOS
# ------------------------------------------------------------------------------
with tab_dashboard:
    st.subheader("📝 Resumen Ejecutivo del Inventario")

    costo_compra, costo_almacen, costo_faltantes = calcular_costos_estaticos(df_inventario)
    costo_total_sistema = costo_compra + costo_almacen + costo_faltantes
    num_agotados = int((df_inventario["Stock Actual"] == 0).sum())

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)
    with kpi_col1:
        st.metric(
            label="Costo Total de Compra",
            value=f"${costo_compra:,.2f}",
            help="Inversión total requerida para adquirir el stock actual (Σ Costo Compra * Stock Actual).",
        )
    with kpi_col2:
        st.metric(
            label="Costo de Almacenamiento",
            value=f"${costo_almacen:,.2f}",
            help="Costo periódico de mantenimiento físico y conservación (Σ Costo Almacén * Stock Actual).",
        )
    with kpi_col3:
        st.metric(
            label="Lucro Cesante (Faltantes)",
            value=f"${costo_faltantes:,.2f}",
            delta=f"{num_agotados} agotado(s)" if num_agotados > 0 else "0 agotados",
            delta_color="inverse" if num_agotados > 0 else "normal",
            help="Pérdida económica por demanda insatisfecha en productos con stock en 0.",
        )
    with kpi_col4:
        st.metric(
            label="Costo Total del Sistema",
            value=f"${costo_total_sistema:,.2f}",
            help="Suma total de costos operativos: Compra + Almacenamiento + Lucro Cesante.",
        )

    # Alertas
    st.subheader("🚨 Diagnóstico y Alertas de Stock")
    alertas_encontradas = 0
    for _, fila in df_inventario.iterrows():
        producto = fila["Producto"]
        stock_actual = int(fila["Stock Actual"])
        stock_minimo = int(fila["Stock Mínimo"])
        margen_unitario = float(fila["Margen Unitario ($)"])

        if stock_actual == 0:
            alertas_encontradas += 1
            lucro_cesante_prod = margen_unitario * stock_minimo
            st.error(
                f"🛑 **STOCK AGOTADO:** **{producto}** se encuentra en 0 unidades.\n\n"
                f"Se activa penalización por **Lucro Cesante:** **${lucro_cesante_prod:,.2f}** "
                f"(Pérdida estimada de {stock_minimo} unidades a ${margen_unitario:,.2f} de margen unitario).",
                icon="🚨",
            )
        elif stock_actual < stock_minimo:
            alertas_encontradas += 1
            st.warning(
                f"⚠️ **STOCK POR DEBAJO DEL MÍNIMO:** **{producto}** cuenta con "
                f"**{stock_actual}** unidades (Mínimo requerido: {stock_minimo}). "
                f"Sugerido emitir orden de reabastecimiento.",
                icon="⚠️",
            )

    if alertas_encontradas == 0:
        st.success(
            "**ESTADO ÓPTIMO:** Todos los productos se encuentran en o por encima de su Stock Mínimo. "
            "_No se detectan faltantes ni riesgos operativos._",
            icon="✅",
        )

    # Gráficas visuales integradas del estado actual
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.plotly_chart(graficar_estado_inventario(df_inventario), use_container_width=True)
    with col_v2:
        st.plotly_chart(graficar_valor_comercial(df_inventario), use_container_width=True)

    st.markdown("---")

    # Tabla con totales
    st.subheader("📋 Estado Actual del Inventario")
    df_visual = df_inventario.copy()
    df_visual["Valor Comercial ($)"] = df_visual["Precio Venta ($)"] * df_visual["Stock Actual"]

    fila_totales = pd.DataFrame(
        [
            {
                "Producto": "TOTALES",
                "Precio Venta ($)": None,
                "Costo Compra ($)": float((df_visual["Costo Compra ($)"] * df_visual["Stock Actual"]).sum()),
                "Margen Unitario ($)": float((df_visual["Margen Unitario ($)"] * df_visual["Stock Actual"]).sum()),
                "Costo Almacenamiento ($/unidad)": float(
                    (df_visual["Costo Almacenamiento ($/unidad)"] * df_visual["Stock Actual"]).sum()
                ),
                "Stock Actual": int(df_visual["Stock Actual"].sum()),
                "Stock Mínimo": int(df_visual["Stock Mínimo"].sum()),
                "Valor Comercial ($)": float(df_visual["Valor Comercial ($)"].sum()),
            }
        ]
    )
    df_visual = pd.concat([df_visual, fila_totales], ignore_index=True)

    df_styled = df_visual.style.apply(
        lambda row: [
            "font-weight: bold; background-color: rgba(128, 128, 128, 0.1);"
            if row["Producto"] == "TOTALES"
            else ""
            for _ in row
        ],
        axis=1,
    )

    column_config = {
        "Producto": st.column_config.TextColumn("Producto"),
        "Precio Venta ($)": st.column_config.NumberColumn("Precio Venta", format="$%.2f"),
        "Costo Compra ($)": st.column_config.NumberColumn("Costo Compra", format="$%.2f"),
        "Margen Unitario ($)": st.column_config.NumberColumn("Margen Unitario", format="$%.2f"),
        "Costo Almacenamiento ($/unidad)": st.column_config.NumberColumn("Costo Almacén", format="$%.2f"),
        "Stock Actual": st.column_config.NumberColumn("Stock Actual", format="%d unid."),
        "Stock Mínimo": st.column_config.NumberColumn("Stock Mínimo", format="%d unid."),
        "Valor Comercial ($)": st.column_config.NumberColumn("Valor Comercial", format="$%.2f"),
    }

    st.dataframe(
        df_styled,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
    )

# ------------------------------------------------------------------------------
# PESTAÑA 2: MÓDULO 2 — SIMULACIÓN DISCRETA
# ------------------------------------------------------------------------------
with tab_discreta:
    render_modulo_simulacion_discreta(df_inventario)

# ------------------------------------------------------------------------------
# PESTAÑA 3: MÓDULO 3 — MODELO CONTINUO (EDO)
# ------------------------------------------------------------------------------
with tab_continuo:
    render_modulo_continuo(df_inventario)

# ------------------------------------------------------------------------------
# PESTAÑA 4: MÓDULO 4 — EXPERIMENTACIÓN Y OPTIMIZACIÓN
# ------------------------------------------------------------------------------
with tab_optimo:
    render_modulo_control_optimo(df_inventario)