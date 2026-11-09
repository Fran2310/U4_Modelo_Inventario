"""
==============================================================================
SISTEMA DE GESTIÓN Y SIMULACIÓN DE INVENTARIO PARA SUPERMERCADO
==============================================================================
Descripción:
    Script principal de la aplicación interactiva para la administración y
    control de inventarios. Administra el estado centralizado del stock
    mediante st.session_state, permite operaciones de entrada y salida (CRUD),
    calcula dinámicamente la estructura de costos operativos evaluando el lucro
    cesante por roturas de stock, y emite alertas tempranas según los umbrales
    mínimos de existencia.

Ejecución:
    streamlit run main.py
==============================================================================
"""

from typing import Tuple
import pandas as pd
import streamlit as st

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
        # Cálculo dinámico del margen unitario de ganancia
        df["Margen Unitario ($)"] = df["Precio Venta ($)"] - df["Costo Compra ($)"]
        
        # Orden preferente de columnas para claridad financiera
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
        # Mecanismo de seguridad: garantizar cálculo de margen si se proviene de sesión previa
        df = st.session_state[SESSION_KEY_INVENTARIO]
        if "Margen Unitario ($)" not in df.columns:
            df["Margen Unitario ($)"] = df["Precio Venta ($)"] - df["Costo Compra ($)"]
            st.session_state[SESSION_KEY_INVENTARIO] = df


def reiniciar_inventario() -> None:
    """Restaura los valores predeterminados del inventario en session_state."""
    if SESSION_KEY_INVENTARIO in st.session_state:
        del st.session_state[SESSION_KEY_INVENTARIO]
    inicializar_inventario()


# Ejecutar inicialización garantizada al cargar el script
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

    Parámetros:
        df (pd.DataFrame): DataFrame con el estado actual del inventario.

    Retorna:
        Tuple[float, float, float]:
            - costo_total_compra: Inversión en adquisición del stock en almacén.
            - costo_total_almacenamiento: Gasto operativo de mantenimiento y conservación.
            - costo_faltantes: Pérdida económica total por Lucro Cesante (demanda insatisfecha).
    """
    # 1. Costo Total de Compra
    costo_total_compra = float((df["Costo Compra ($)"] * df["Stock Actual"]).sum())

    # 2. Costo Total de Almacenamiento
    costo_total_almacenamiento = float(
        (df["Costo Almacenamiento ($/unidad)"] * df["Stock Actual"]).sum()
    )

    # 3. Costo de Faltantes / Lucro Cesante:
    # Penalización por demanda insatisfecha = Margen Unitario ($) * Stock Mínimo
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
    """
    Incrementa el stock actual de un producto en el DataFrame de session_state.
    """
    df = st.session_state[SESSION_KEY_INVENTARIO]
    idx = df[df["Producto"] == producto].index
    if not idx.empty:
        df.loc[idx, "Stock Actual"] += cantidad
        st.session_state[SESSION_KEY_INVENTARIO] = df
        st.toast(f"✅ Se agregaron {cantidad} unidades a **{producto}**.", icon="📥")


def retirar_stock(producto: str, cantidad: int) -> bool:
    """
    Disminuye el stock actual de un producto asegurando que no caiga por debajo de 0.

    Retorna:
        bool: True si la operación fue exitosa, False si no hay stock suficiente.
    """
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
# BARRA LATERAL: CONTROLES CRUD Y ACCIONES
# ==============================================================================
with st.sidebar:
    st.header("📦 Gestión de Inventario")
    st.caption("Entradas y Salidas Manuales de Mercancía")

    df_actual = st.session_state[SESSION_KEY_INVENTARIO]
    lista_productos = df_actual["Producto"].tolist()

    # Selector de producto
    producto_seleccionado = st.selectbox(
        "Seleccionar Producto:",
        options=lista_productos,
        help="Elige el artículo sobre el cual registrar el movimiento.",
    )

    # Cantidad a mover
    cantidad_movimiento = st.number_input(
        "Cantidad de Unidades:",
        min_value=1,
        value=10,
        step=1,
        help="Número de unidades a ingresar o retirar del almacén.",
    )

    # Botones de acción en dos columnas
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

    # Opciones de mantenimiento / reinicio
    with st.expander("⚙️ Opciones del Sistema"):
        st.write("Restaura los valores base de inventario para pruebas y calibración.")
        if st.button("🔄 Reiniciar Inventario Base", use_container_width=True):
            reiniciar_inventario()
            st.rerun()


# ==============================================================================
# INTERFAZ PRINCIPAL (DASHBOARD)
# ==============================================================================
st.title("🛒 Inventario Supermercado")
st.subheader("Resumen", icon="📝")
# ------------------------------------------------------------------------------
# 1. CÁLCULO DE COSTOS Y TARJETAS DE MÉTRICAS (KPIs)
# ------------------------------------------------------------------------------
df_inventario = st.session_state[SESSION_KEY_INVENTARIO]
costo_compra, costo_almacen, costo_faltantes = calcular_costos_estaticos(df_inventario)
costo_total_sistema = costo_compra + costo_almacen + costo_faltantes
num_agotados = int((df_inventario["Stock Actual"] == 0).sum())

# Fila principal de métricas
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
        help="Pérdida económica por demanda insatisfecha (Σ Margen Unitario * Stock Mínimo) en productos con stock en 0.",
    )

with kpi_col4:
    st.metric(
        label="Costo Total del Sistema",
        value=f"${costo_total_sistema:,.2f}",
        help="Suma total de costos operativos: Compra + Almacenamiento + Lucro Cesante por faltantes.",
    )

# ------------------------------------------------------------------------------
# 2. DIAGNÓSTICO Y ALERTAS DE STOCK (BLOQUE SUPERIOR)
# ------------------------------------------------------------------------------
st.subheader("🚨 Diagnóstico y Alertas de Stock")
alertas_encontradas = 0

for _, fila in df_inventario.iterrows():
    producto = fila["Producto"]
    stock_actual = int(fila["Stock Actual"])
    stock_minimo = int(fila["Stock Mínimo"])
    margen_unitario = float(fila["Margen Unitario ($)"])

    # Nivel 1: Rotura Crítica de Stock (Stock == 0) -> Lucro Cesante
    if stock_actual == 0:
        alertas_encontradas += 1
        lucro_cesante_prod = margen_unitario * stock_minimo
        st.error(
            f"🛑 **STOCK AGOTADO:** **{producto}** se encuentra en 0 unidades.\n\n"
            f"Se activa penalización por **Lucro Cesante:** **${lucro_cesante_prod:,.2f}** "
            f"(Pérdida estimada de {stock_minimo} unidades de demanda a ${margen_unitario:,.2f} de margen unitario).",
            icon="🚨",
        )

    # Nivel 2: Advertencia de Stock Bajo (Stock < Stock Mínimo) -> st.warning
    elif stock_actual < stock_minimo:
        alertas_encontradas += 1
        st.warning(
            f"⚠️ **STOCK POR DEBAJO DEL MÍNIMO:** **{producto}** cuenta con "
            f"**{stock_actual}** unidades (Mínimo requerido: {stock_minimo}). "
            f"Sugerido emitir orden de reabastecimiento.",
            icon="⚠️",
        )

# Estado saludable si no existen alertas
if alertas_encontradas == 0:
    st.success(
        "**ESTADO ÓPTIMO:** Todos los productos se encuentran en o por encima de su Stock Mínimo. "
        "_No se detectan faltantes ni riesgos operativos._",
        icon="✅",
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 3. TABLA DE INVENTARIO (CON FILA DINÁMICA DE TOTALES)
# ------------------------------------------------------------------------------
st.subheader("📋 Estado Actual del Inventario")

# Generación al vuelo del DataFrame visual (para no contaminar el estado de sesión ni el CRUD)
df_visual = df_inventario.copy()

# Columna analítica: Valor Comercial ($) = Precio Venta ($) * Stock Actual
df_visual["Valor Comercial ($)"] = (
    df_visual["Precio Venta ($)"] * df_visual["Stock Actual"]
)

# Cálculo de totales agregados
total_stock = int(df_visual["Stock Actual"].sum())
total_valor_comercial = float(df_visual["Valor Comercial ($)"].sum())

# Fila consolidada de TOTALES
fila_totales = pd.DataFrame(
    [
        {
            "Producto": "TOTALES",
            "Precio Venta ($)": None,
            "Costo Compra ($)": None,
            "Margen Unitario ($)": None,
            "Costo Almacenamiento ($/unidad)": None,
            "Stock Actual": total_stock,
            "Stock Mínimo": None,
            "Valor Comercial ($)": total_valor_comercial,
        }
    ]
)

df_visual = pd.concat([df_visual, fila_totales], ignore_index=True)

# Estilización con Pandas Styler: fila de TOTALES en negrita con fondo tenue
df_styled = df_visual.style.apply(
    lambda row: [
        "font-weight: bold; background-color: rgba(128, 128, 128, 0.1);"
        if row["Producto"] == "TOTALES"
        else ""
        for _ in row
    ],
    axis=1,
)

# Configuración visual de columnas
column_config = {
    "Producto": st.column_config.TextColumn(
        "Producto",
        help="Categoría clave del supermercado o fila de consolidado",
    ),
    "Precio Venta ($)": st.column_config.NumberColumn(
        "Precio Venta",
        format="$%.2f",
        help="Precio al público consumidor",
    ),
    "Costo Compra ($)": st.column_config.NumberColumn(
        "Costo Compra",
        format="$%.2f",
        help="Costo unitario con proveedores",
    ),
    "Margen Unitario ($)": st.column_config.NumberColumn(
        "Margen Unitario",
        format="$%.2f",
        help="Margen de ganancia unitario (Precio Venta - Costo Compra)",
    ),
    "Costo Almacenamiento ($/unidad)": st.column_config.NumberColumn(
        "Costo Almacén",
        format="$%.2f",
        help="Costo de almacenaje/refrigeración unitario",
    ),
    "Stock Actual": st.column_config.NumberColumn(
        "Stock Actual",
        format="%d unid.",
        help="Nivel físico actual en estantería/bodega",
    ),
    "Stock Mínimo": st.column_config.NumberColumn(
        "Stock Mínimo",
        format="%d unid.",
        help="Umbral de seguridad (punto de reorden)",
    ),
    "Valor Comercial ($)": st.column_config.NumberColumn(
        "Valor Comercial",
        format="$%.2f",
        help="Valor comercial del inventario (Precio Venta * Stock Actual)",
    ),
}

# Renderizado de la tabla a ancho completo
st.dataframe(
    df_styled,
    use_container_width=True,
    hide_index=True,
    column_config=column_config,
)
