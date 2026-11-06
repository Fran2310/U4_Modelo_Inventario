"""
==============================================================================
SIMULADOR DE INVENTARIO PARA SUPERMERCADO
Materia: DCM-902 - Diseño y Control de Modelos
Módulo 1: Core de Inventario y Modelo Estático
==============================================================================
Descripción:
    Este script constituye la base funcional y la interfaz gráfica (Dashboard)
    del simulador de inventario. Administra el estado global del inventario
    mediante st.session_state, proporciona operaciones manuales de inventario
    (CRUD: entradas y salidas), evalúa un modelo estático de costos y emite
    alertas operativas en función de umbrales de seguridad.

Arquitectura por Módulos:
    - [Módulo 1] Core de Inventario y Modelo Estático (ESTE ARCHIVO)
    - [Módulo 2] Simulación de Eventos Discretos / Demanda Estocástica (Próximo)
    - [Módulo 3] Modelado Continuo y Degradación / Mermas (Próximo)
    - [Módulo 4] Optimización y Políticas de Control (s, S / EOQ) (Próximo)

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

# Constante de penalización ficticia por rotura de stock ($ por producto agotado)
PENALIZACION_FALTANTE_POR_PRODUCTO: float = 150.0

# Clave utilizada para almacenar el DataFrame en st.session_state
SESSION_KEY_INVENTARIO: str = "inventario_df"


# ==============================================================================
# GESTIÓN DE ESTADO (st.session_state)
# ==============================================================================
def inicializar_inventario() -> None:
    """
    Inicializa el DataFrame de inventario en st.session_state con los 4 productos
    clave del supermercado y parámetros realistas si aún no ha sido creado.
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
        st.session_state[SESSION_KEY_INVENTARIO] = pd.DataFrame(datos_iniciales)


def reiniciar_inventario() -> None:
    """Restaura los valores predeterminados del inventario en session_state."""
    if SESSION_KEY_INVENTARIO in st.session_state:
        del st.session_state[SESSION_KEY_INVENTARIO]
    inicializar_inventario()


# Ejecutar inicialización garantizada al cargar el script
inicializar_inventario()


# ==============================================================================
# MODELO ESTÁTICO: CALCULADORA PURA DE COSTOS
# ==============================================================================
def calcular_costos_estaticos(df: pd.DataFrame) -> Tuple[float, float, float]:
    """
    Función pura que calcula y retorna los costos estáticos del inventario
    basándose en el estado actual de los datos.

    Fórmulas:
        1. Costo Total de Compra = Σ (Costo Compra ($) * Stock Actual)
        2. Costo Total de Almacenamiento = Σ (Costo Almacenamiento ($/unidad) * Stock Actual)
        3. Costo de Faltantes/Pérdidas = Número de productos con Stock == 0 * PENALIZACION

    Parámetros:
        df (pd.DataFrame): DataFrame con el estado actual del inventario.

    Retorna:
        Tuple[float, float, float]:
            - costo_total_compra: Inversión en adquisición del stock en almacén.
            - costo_total_almacenamiento: Gasto operativo de mantenimiento/refrigeración.
            - costo_faltantes: Penalización económica por roturas de stock (Stock = 0).
    """
    # 1. Costo Total de Compra
    costo_total_compra = float((df["Costo Compra ($)"] * df["Stock Actual"]).sum())

    # 2. Costo Total de Almacenamiento
    costo_total_almacenamiento = float(
        (df["Costo Almacenamiento ($/unidad)"] * df["Stock Actual"]).sum()
    )

    # 3. Costo de Faltantes/Pérdidas (Penalización por rotura de stock cuando Stock Actual == 0)
    productos_agotados = int((df["Stock Actual"] == 0).sum())
    costo_faltantes = float(productos_agotados * PENALIZACION_FALTANTE_POR_PRODUCTO)

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

    st.markdown("---")
    st.info(
        "**Módulo 1:** Core de Inventario y Modelo Estático\n\n"
        "*Los módulos de simulación dinámica (M2) y control continuo (M3) "
        "se integrarán en etapas posteriores.*"
    )


# ==============================================================================
# INTERFAZ PRINCIPAL (DASHBOARD)
# ==============================================================================
st.title("🛒 Dashboard de Control y Gestión de Inventario")
st.markdown(
    "**Materia:** DCM-902 Diseño y Control de Modelos &nbsp;|&nbsp; "
    "**Etapa:** Módulo 1 (Core & Modelo Estático)"
)
st.write(
    "Monitoreo centralizado del nivel de existencias, cálculo analítico de costos "
    "operativos y sistema temprano de alertas para supermercados."
)

st.markdown("---")

# ------------------------------------------------------------------------------
# 1. CÁLCULO DE COSTOS ESTÁTICOS Y TARJETAS DE MÉTRICAS (KPIs)
# ------------------------------------------------------------------------------
df_inventario = st.session_state[SESSION_KEY_INVENTARIO]
costo_compra, costo_almacen, costo_faltantes = calcular_costos_estaticos(df_inventario)
costo_total_sistema = costo_compra + costo_almacen + costo_faltantes
num_agotados = int((df_inventario["Stock Actual"] == 0).sum())

# Mostrar métricas principales usando st.columns
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
        help="Costo periódico de mantenimiento físico y refrigeración (Σ Costo Almacén * Stock Actual).",
    )

with kpi_col3:
    st.metric(
        label="Costo de Faltantes / Pérdidas",
        value=f"${costo_faltantes:,.2f}",
        delta=f"{num_agotados} agotado(s)" if num_agotados > 0 else "0 agotados",
        delta_color="inverse" if num_agotados > 0 else "normal",
        help=f"Penalización de ${PENALIZACION_FALTANTE_POR_PRODUCTO:,.2f} aplicada por cada producto sin stock.",
    )

with kpi_col4:
    st.metric(
        label="Costo Total del Sistema",
        value=f"${costo_total_sistema:,.2f}",
        help="Suma integral del Modelo Estático: Compra + Almacenamiento + Penalizaciones.",
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 2. CUERPO PRINCIPAL: TABLA DE DATOS Y PANEL DE ALERTAS
# ------------------------------------------------------------------------------
col_tabla, col_alertas = st.columns([1.6, 1.0], gap="large")

with col_tabla:
    st.subheader("📋 Estado Actual del Inventario")
    st.caption("Valores sincronizados en tiempo real mediante `st.session_state`.")

    # Visualización profesional del DataFrame con formato de columnas
    st.dataframe(
        df_inventario,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Producto": st.column_config.TextColumn(
                "Producto",
                help="Categoría clave del supermercado",
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
            "Costo Almacenamiento ($/unidad)": st.column_config.NumberColumn(
                "Costo Almacén",
                format="$%.2f",
                help="Costo de almacenaje/refrigeración unitario",
            ),
            "Stock Actual": st.column_config.ProgressColumn(
                "Stock Actual",
                format="%d unid.",
                min_value=0,
                max_value=300,
                help="Nivel físico actual en estantería/bodega",
            ),
            "Stock Mínimo": st.column_config.NumberColumn(
                "Stock Mínimo",
                format="%d unid.",
                help="Umbral de seguridad (punto de reorden)",
            ),
        },
    )

    # Resumen rápido de totales físicos
    unidades_totales = int(df_inventario["Stock Actual"].sum())
    valor_venta_potencial = float(
        (df_inventario["Precio Venta ($)"] * df_inventario["Stock Actual"]).sum()
    )
    st.caption(
        f"📦 **Total unidades en almacén:** {unidades_totales:,} unidades | "
        f"💰 **Valor comercial estimado:** ${valor_venta_potencial:,.2f}"
    )


with col_alertas:
    st.subheader("🚨 Diagnóstico y Alertas de Stock")
    st.caption("Monitoreo automático de umbrales críticos de inventario.")

    # Sistema de alertas: Iteración sobre el DataFrame
    alertas_encontradas = 0

    for _, fila in df_inventario.iterrows():
        producto = fila["Producto"]
        stock_actual = int(fila["Stock Actual"])
        stock_minimo = int(fila["Stock Mínimo"])

        # Nivel 1: Rotura Crítica de Stock (Stock == 0) -> st.error
        if stock_actual == 0:
            alertas_encontradas += 1
            st.error(
                f"🛑 **STOCK AGOTADO:** **{producto}** se encuentra en 0 unidades.\n\n"
                f"Se activa penalización de faltante (+${PENALIZACION_FALTANTE_POR_PRODUCTO:,.2f}).",
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
            "✅ **ESTADO ÓPTIMO:** Todos los productos superan holgadamente su Stock Mínimo. "
            "No se detectan faltantes ni riesgos operativos.",
            icon="✨",
        )


# ==============================================================================
# SECCIÓN DOCUMENTAL Y HOOKS DE INTEGRACIÓN (PARA COMPAÑEROS DE EQUIPO)
# ==============================================================================
with st.expander("📚 Guía de Arquitectura e Integración (Módulos 2, 3 y 4)"):
    st.markdown(
        """
        ### Estructura del Proyecto DCM-902:
        Esta aplicación sirve como base para integrar los módulos analíticos del proyecto:

        ```
        U4_Modelo_Inventario/
        │
        ├── main.py                  # [Módulo 1] Core, UI y Modelo Estático (Presente)
        ├── simulacion_discreta.py   # [Módulo 2] Simulación de demanda por eventos (Monte Carlo)
        ├── modelo_continuo.py       # [Módulo 3] Ecuaciones diferenciales y perecederos
        ├── control_optimo.py        # [Módulo 4] Política de inventarios óptima (s, S / EOQ)
        └── requirements.txt         # Dependencias del entorno virtual
        ```

        #### Puntos de Inyección para los siguientes módulos:
        1. **Módulo 2 (Simulación Discreta):**
           - Podrá recibir `st.session_state['inventario_df']` como condición inicial $t_0$.
           - Iterará la demanda diaria mediante variables aleatorias (ej. Poisson / Normal).
        2. **Módulo 3 (Modelos Continuos):**
           - Añadirá dinámicas de degradación continua sobre productos perecederos (ej. *Carne* y *Lácteos*).
           - Aplicará integradores numéricos (`scipy.integrate.solve_ivp` o Euler).
        3. **Módulo 4 (Políticas de Control):**
           - Recibirá las salidas simuladas para calcular los parámetros óptimos $(s, S)$
             minimizando la función de costo estático definida en `calcular_costos_estaticos()`.
        """
    )
