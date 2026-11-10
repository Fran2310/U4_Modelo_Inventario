"""
==============================================================================
SISTEMA DE GESTIÓN Y SIMULACIÓN DE INVENTARIO PARA SUPERMERCADO
==============================================================================
Incluye:
    - CRUD manual sobre st.session_state (Agregar / Retirar / Reiniciar).
    - Calculadora estática de costos (compra, almacenamiento, lucro cesante).
    - Alertas automáticas (stock bajo / agotado).
    - Simulación discreta secuencial de intervalos (30 días).
    - Simulación de demanda estocástica (distribución normal).
    - Políticas de reposición: (s, Q) continua y (R, S) periódica.
    - Modelo dinámico continuo: temperatura del almacén (ecuación senoidal).
    - Modelo híbrido: merma de producto cuando la temperatura excede un umbral.
    - Comparación de costos entre políticas.
    - Optimización por barrido de parámetros.

Ejecución:
    streamlit run main.py
==============================================================================
"""

from typing import Tuple
import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go

# ==============================================================================
# CONFIGURACIÓN GENERAL
# ==============================================================================
st.set_page_config(
    page_title="Simulador de Inventario | Supermercado",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

SESSION_KEY_INVENTARIO: str = "inventario_df"


# ==============================================================================
# GESTIÓN DE ESTADO (st.session_state)
# ==============================================================================
def inicializar_inventario() -> None:
    """Inicializa el DataFrame de inventario con 4 productos base."""
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
            "Producto", "Precio Venta ($)", "Costo Compra ($)",
            "Margen Unitario ($)", "Costo Almacenamiento ($/unidad)",
            "Stock Actual", "Stock Mínimo",
        ]
        st.session_state[SESSION_KEY_INVENTARIO] = df[columnas_ordenadas]
    else:
        df = st.session_state[SESSION_KEY_INVENTARIO]
        if "Margen Unitario ($)" not in df.columns:
            df["Margen Unitario ($)"] = df["Precio Venta ($)"] - df["Costo Compra ($)"]
            st.session_state[SESSION_KEY_INVENTARIO] = df


def reiniciar_inventario() -> None:
    """Restaura los valores base del inventario."""
    if SESSION_KEY_INVENTARIO in st.session_state:
        del st.session_state[SESSION_KEY_INVENTARIO]
    inicializar_inventario()


inicializar_inventario()


# ==============================================================================
# CALCULADORA PURA DE COSTOS ESTÁTICOS
# ==============================================================================
def calcular_costos_estaticos(df: pd.DataFrame) -> Tuple[float, float, float]:
    """Costo de compra, almacenamiento y lucro cesante (faltantes)."""
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
# OPERACIONES CRUD
# ==============================================================================
def agregar_stock(producto: str, cantidad: int) -> None:
    df = st.session_state[SESSION_KEY_INVENTARIO]
    idx = df[df["Producto"] == producto].index
    if not idx.empty:
        df.loc[idx, "Stock Actual"] += cantidad
        st.session_state[SESSION_KEY_INVENTARIO] = df
        st.toast(f"✅ Se agregaron {cantidad} unidades a **{producto}**.", icon="📥")


def retirar_stock(producto: str, cantidad: int) -> bool:
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
# MOTOR DE SIMULACIÓN DISCRETA (MODELO SECUENCIAL DE INTERVALOS)
# ==============================================================================
def simular(
    prod: pd.Series,
    politica: str,
    dias: int,
    lead_time: int,
    dem_mean: float,
    dem_std: float,
    s: int,
    Q: int,
    R: int,
    S: int,
    temp_base: float,
    temp_amp: float,
    temp_umbral: float,
    merma_pct: float,
) -> pd.DataFrame:
    """
    Simulación discreta secuencial día a día.

    Modelos aplicados:
        - Simulación de demanda estocástica (N(μ, σ)).
        - Política (s, Q): pedir Q cuando la posición de inventario ≤ s.
        - Política (R, S): cada R días, pedir hasta S.
        - Temperatura dinámica: T(t) = base + A·sin(2π·t/30).
        - Merma por calor cuando T > umbral (modelo híbrido).

    La decisión de pedido usa la POSICIÓN DE INVENTARIO (stock + pedidos
    en tránsito) para evitar generar pedidos duplicados mientras llega
    el lead time.
    """
    rng = np.random.default_rng(42)
    stock = int(prod["Stock Actual"])
    pipeline = []          # [(día_llegada, cantidad)]
    historial = []

    for dia in range(1, dias + 1):
        # 1) Llegada de pedidos pendientes
        stock += sum(q for d, q in pipeline if d == dia)
        pipeline = [(d, q) for d, q in pipeline if d > dia]

        # 2) Demanda estocástica
        demanda = max(0, int(round(rng.normal(dem_mean, dem_std))))
        ventas = min(stock, demanda)
        faltantes = demanda - ventas
        stock -= ventas

        # 3) Temperatura dinámica: T(t) = base + A·sin(2π·t/30)
        temp = temp_base + temp_amp * np.sin(2 * np.pi * dia / 30)

        # 4) Merma por calor (modelo híbrido)
        merma = 0
        if temp > temp_umbral and stock > 0:
            merma = int(round(stock * merma_pct))
            stock -= merma

        # 5) Posición de inventario (stock físico + pedidos en tránsito)
        en_transito = sum(q for _, q in pipeline)
        posicion = stock + en_transito

        # 6) Decisión de pedido según política
        pedido = 0
        if politica == "sQ":
            if posicion <= s:
                pedido = Q
        else:  # "RS"
            if dia % R == 0 and posicion < S:
                pedido = S - posicion

        if pedido > 0:
            pipeline.append((dia + lead_time, pedido))

        historial.append({
            "Día": dia,
            "Demanda": demanda,
            "Ventas": ventas,
            "Faltantes": faltantes,
            "Temp (°C)": round(temp, 2),
            "Merma": merma,
            "Pedido": pedido,
            "Stock Final": stock,
        })

    return pd.DataFrame(historial)


def costos_simulacion(df: pd.DataFrame, prod: pd.Series) -> dict:
    """Convierte la simulación diaria en costos monetarios."""
    c_compra = df["Pedido"].sum() * prod["Costo Compra ($)"]
    c_almacen = df["Stock Final"].mean() * prod["Costo Almacenamiento ($/unidad)"] * len(df)
    c_falt = df["Faltantes"].sum() * prod["Margen Unitario ($)"]
    c_merma = df["Merma"].sum() * prod["Costo Compra ($)"]
    return {
        "Costo Compra ($)": c_compra,
        "Costo Almacenamiento ($)": c_almacen,
        "Lucro Cesante ($)": c_falt,
        "Pérdida Merma ($)": c_merma,
        "Costo Total ($)": c_compra + c_almacen + c_falt + c_merma,
        "Faltantes (unid)": int(df["Faltantes"].sum()),
    }


# ==============================================================================
# BARRA LATERAL: CRUD + PARÁMETROS DE SIMULACIÓN
# ==============================================================================
with st.sidebar:
    st.header("📦 Gestión de Inventario")
    st.caption("Entradas y Salidas Manuales")

    df_actual = st.session_state[SESSION_KEY_INVENTARIO]
    lista_productos = df_actual["Producto"].tolist()

    producto_seleccionado = st.selectbox(
        "Seleccionar Producto:", lista_productos, key="prod_crud",
    )
    cantidad_movimiento = st.number_input(
        "Cantidad de Unidades:", min_value=1, value=10, step=1, key="qty_crud",
    )

    col_btn_add, col_btn_sub = st.columns(2)
    with col_btn_add:
        if st.button("📥 Agregar", use_container_width=True, type="primary"):
            agregar_stock(producto_seleccionado, int(cantidad_movimiento))
            st.rerun()
    with col_btn_sub:
        if st.button("📤 Retirar", use_container_width=True):
            if not retirar_stock(producto_seleccionado, int(cantidad_movimiento)):
                stock_disp = df_actual.loc[
                    df_actual["Producto"] == producto_seleccionado, "Stock Actual"
                ].values[0]
                st.error(f"⚠️ Stock insuficiente. Disponible: {stock_disp} unidades.")
            else:
                st.rerun()

    with st.expander("⚙️ Opciones del Sistema"):
        if st.button("🔄 Reiniciar Inventario Base", use_container_width=True):
            reiniciar_inventario()
            st.rerun()

    # --------- PARÁMETROS DE SIMULACIÓN ---------
    st.divider()
    st.header("🎲 Parámetros de Simulación")

    producto_sim = st.selectbox(
        "Producto a simular:", lista_productos, key="prod_sim",
    )
    dias = st.number_input("Días a simular:", 10, 90, 30, key="dias_sim")
    lead_time = st.number_input("Lead time (días):", 0, 10, 3, key="lt_sim")

    st.subheader("Demanda estocástica")
    dem_mean = st.number_input("Demanda media diaria:", 1, 100, 20, key="dm")
    dem_std = st.number_input("Desviación estándar:", 0, 30, 5, key="ds")

    st.subheader("Política (s, Q) — Continua")
    s_val = st.slider("s (punto de reorden):", 0, 150, 20, key="s_pol")
    Q_val = st.slider("Q (cantidad pedido):", 10, 300, 50, key="q_pol")

    st.subheader("Política (R, S) — Periódica")
    R_val = st.slider("R (periodo revisión):", 1, 15, 5, key="r_pol")
    S_val = st.slider("S (nivel objetivo):", 50, 400, 150, key="s_obj")

    st.subheader("🌡️ Temperatura (modelo dinámico)")
    temp_base = st.slider("Temperatura base (°C):", 10.0, 30.0, 20.0, key="tb")
    temp_amp = st.slider("Amplitud térmica (°C):", 0.0, 15.0, 8.0, key="ta")
    temp_umbral = st.slider("Umbral crítico (°C):", 15.0, 40.0, 26.0, key="tu")
    merma_pct = st.slider("Tasa de merma por calor:", 0.0, 0.20, 0.03, key="mp")


# ==============================================================================
# INTERFAZ PRINCIPAL — DASHBOARD CRUD
# ==============================================================================
st.title("🛒 Inventario Supermercado")
st.subheader("📝 Resumen del Estado Actual")

df_inventario = st.session_state[SESSION_KEY_INVENTARIO]
costo_compra, costo_almacen, costo_faltantes = calcular_costos_estaticos(df_inventario)
costo_total_sistema = costo_compra + costo_almacen + costo_faltantes
num_agotados = int((df_inventario["Stock Actual"] == 0).sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Costo Total de Compra", f"${costo_compra:,.2f}")
k2.metric("Costo de Almacenamiento", f"${costo_almacen:,.2f}")
k3.metric(
    "Lucro Cesante",
    f"${costo_faltantes:,.2f}",
    delta=f"{num_agotados} agotado(s)" if num_agotados else "0 agotados",
    delta_color="inverse" if num_agotados else "normal",
)
k4.metric("Costo Total del Sistema", f"${costo_total_sistema:,.2f}")

# Alertas
st.subheader("🚨 Diagnóstico y Alertas de Stock")
alertas = 0
for _, fila in df_inventario.iterrows():
    prod, stock, minimo = fila["Producto"], int(fila["Stock Actual"]), int(fila["Stock Mínimo"])
    margen = float(fila["Margen Unitario ($)"])
    if stock == 0:
        alertas += 1
        st.error(
            f"🛑 **STOCK AGOTADO:** **{prod}** (0 unid). "
            f"Lucro cesante activo: **${margen * minimo:,.2f}**."
        )
    elif stock < minimo:
        alertas += 1
        st.warning(f"⚠️ **STOCK BAJO:** **{prod}** — {stock} unid. (mínimo: {minimo}).")
if alertas == 0:
    st.success("✅ Todos los productos están en o por encima del Stock Mínimo.")

# Tabla de inventario con totales
st.subheader("📋 Estado Actual del Inventario")
df_visual = df_inventario.copy()
df_visual["Valor Comercial ($)"] = df_visual["Precio Venta ($)"] * df_visual["Stock Actual"]

fila_totales = pd.DataFrame([{
    "Producto": "TOTALES",
    "Precio Venta ($)": None,
    "Costo Compra ($)": float((df_visual["Costo Compra ($)"] * df_visual["Stock Actual"]).sum()),
    "Margen Unitario ($)": float((df_visual["Margen Unitario ($)"] * df_visual["Stock Actual"]).sum()),
    "Costo Almacenamiento ($/unidad)": float((df_visual["Costo Almacenamiento ($/unidad)"] * df_visual["Stock Actual"]).sum()),
    "Stock Actual": int(df_visual["Stock Actual"].sum()),
    "Stock Mínimo": int(df_visual["Stock Mínimo"].sum()),
    "Valor Comercial ($)": float(df_visual["Valor Comercial ($)"].sum()),
}])
df_visual = pd.concat([df_visual, fila_totales], ignore_index=True)

df_styled = df_visual.style.apply(
    lambda r: ["font-weight: bold; background-color: rgba(128,128,128,0.1);"
               if r["Producto"] == "TOTALES" else "" for _ in r],
    axis=1,
)

st.dataframe(
    df_styled, use_container_width=True, hide_index=True,
    column_config={
        "Precio Venta ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Costo Compra ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Margen Unitario ($)": st.column_config.NumberColumn(format="$%.2f"),
        "Costo Almacenamiento ($/unidad)": st.column_config.NumberColumn(format="$%.2f"),
        "Stock Actual": st.column_config.NumberColumn(format="%d unid."),
        "Stock Mínimo": st.column_config.NumberColumn(format="%d unid."),
        "Valor Comercial ($)": st.column_config.NumberColumn(format="$%.2f"),
    },
)

st.markdown("---")

# ==============================================================================
# SIMULACIÓN DISCRETA — 30 DÍAS
# ==============================================================================
st.header("📈 Simulación Discreta — Modelo Secuencial de Intervalos")
st.caption(f"Producto simulado: **{producto_sim}** | {dias} días | Lead time: {lead_time} días")

fila_prod = df_inventario[df_inventario["Producto"] == producto_sim].iloc[0]

df_sq = simular(
    fila_prod, "sQ", dias, lead_time, dem_mean, dem_std,
    s_val, Q_val, R_val, S_val,
    temp_base, temp_amp, temp_umbral, merma_pct,
)
df_rs = simular(
    fila_prod, "RS", dias, lead_time, dem_mean, dem_std,
    s_val, Q_val, R_val, S_val,
    temp_base, temp_amp, temp_umbral, merma_pct,
)

cos_sq = costos_simulacion(df_sq, fila_prod)
cos_rs = costos_simulacion(df_rs, fila_prod)

# Gráfico comparativo de stock
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_sq["Día"], y=df_sq["Stock Final"],
                         mode="lines+markers", name="(s,Q) Continua",
                         line=dict(width=3)))
fig.add_trace(go.Scatter(x=df_rs["Día"], y=df_rs["Stock Final"],
                         mode="lines+markers", name="(R,S) Periódica",
                         line=dict(width=3)))
fig.add_hline(y=0, line_dash="dash", line_color="red",
              annotation_text="Quiebre")
fig.add_hline(y=fila_prod["Stock Mínimo"], line_dash="dot", line_color="orange",
              annotation_text="Stock mínimo")
fig.update_layout(title=f"Evolución del stock — {producto_sim}",
                  xaxis_title="Día", yaxis_title="Unidades",
                  hovermode="x unified", height=420)
st.plotly_chart(fig, use_container_width=True)

# Temperatura dinámica
fig_t = go.Figure()
fig_t.add_trace(go.Scatter(x=df_sq["Día"], y=df_sq["Temp (°C)"],
                           mode="lines+markers", name="Temperatura",
                           line=dict(color="firebrick", width=3)))
fig_t.add_hline(y=temp_umbral, line_dash="dash", line_color="orange",
                annotation_text=f"Umbral {temp_umbral}°C")
fig_t.update_layout(
    title="🌡️ Temperatura del almacén — T(t) = base + A·sin(2π·t/30)",
    xaxis_title="Día", yaxis_title="°C", height=320,
)
st.plotly_chart(fig_t, use_container_width=True)

# Comparación de costos
st.subheader("💰 Comparación de Costos por Política")
df_costos = pd.DataFrame([
    {"Política": "(s,Q) Continua", **cos_sq},
    {"Política": "(R,S) Periódica", **cos_rs},
]).set_index("Política").T

st.dataframe(
    df_costos.style.format("${:,.2f}", subset=pd.IndexSlice[
        ["Costo Compra ($)", "Costo Almacenamiento ($)",
         "Lucro Cesante ($)", "Pérdida Merma ($)", "Costo Total ($)"], :
    ]),
    use_container_width=True,
)

mejor = "(s,Q)" if cos_sq["Costo Total ($)"] < cos_rs["Costo Total ($)"] else "(R,S)"
ahorro = abs(cos_sq["Costo Total ($)"] - cos_rs["Costo Total ($)"])
st.success(
    f"🏆 **Recomendación:** la política **{mejor}** ofrece el menor costo total "
    f"(ahorro: **${ahorro:,.2f}**)."
)

# Detalle diario
with st.expander(f"📋 Detalle diario — {producto_sim}"):
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Política (s, Q)")
        st.dataframe(df_sq, use_container_width=True, hide_index=True)
    with col2:
        st.caption("Política (R, S)")
        st.dataframe(df_rs, use_container_width=True, hide_index=True)

st.markdown("---")

# ==============================================================================
# OPTIMIZACIÓN POR BARRIDO
# ==============================================================================
st.header("🔬 Experimentación y Optimización")
st.caption("Barrido automático de parámetros para hallar la configuración de menor costo.")

if st.button("▶️ Ejecutar optimización", type="primary"):
    with st.spinner("Evaluando combinaciones..."):
        resultados = []

        # Barrido (s, Q)
        for s_test in range(5, 100, 15):
            for Q_test in range(20, 200, 40):
                df_t = simular(
                    fila_prod, "sQ", dias, lead_time, dem_mean, dem_std,
                    s_test, Q_test, R_val, S_val,
                    temp_base, temp_amp, temp_umbral, merma_pct,
                )
                c = costos_simulacion(df_t, fila_prod)
                resultados.append({
                    "Política": "(s,Q)", "s": s_test, "Q": Q_test, "R": "-", "S": "-",
                    "Faltantes": c["Faltantes (unid)"],
                    "Costo Total": c["Costo Total ($)"],
                })

        # Barrido (R, S)
        for R_test in range(1, 11, 2):
            for S_test in range(40, 260, 40):
                df_t = simular(
                    fila_prod, "RS", dias, lead_time, dem_mean, dem_std,
                    s_val, Q_val, R_test, S_test,
                    temp_base, temp_amp, temp_umbral, merma_pct,
                )
                c = costos_simulacion(df_t, fila_prod)
                resultados.append({
                    "Política": "(R,S)", "s": "-", "Q": "-", "R": R_test, "S": S_test,
                    "Faltantes": c["Faltantes (unid)"],
                    "Costo Total": c["Costo Total ($)"],
                })

        st.session_state["opt_res"] = pd.DataFrame(resultados).sort_values("Costo Total")

if "opt_res" in st.session_state:
    st.warning(
        "⚠️ Los resultados mostrados fueron calculados con los parámetros vigentes "
        "al pulsar el botón. Si cambias sliders, vuelve a ejecutar para actualizarlos."
    )
    df_opt = st.session_state["opt_res"]
    st.dataframe(
        df_opt.style.format({"Costo Total": "${:,.2f}"}),
        use_container_width=True, hide_index=True,
    )
    top = df_opt.iloc[0]
    st.success(
        f"🥇 **Óptimo:** {top['Política']} — s={top['s']}, Q={top['Q']}, "
        f"R={top['R']}, S={top['S']} → costo ${top['Costo Total']:,.2f} "
        f"con {top['Faltantes']} faltantes."
    )

# ==============================================================================
# MODELOS APLICADOS
# ==============================================================================
with st.expander("📚 Justificación de los modelos de simulación aplicados"):
    st.markdown("""
    - **Modelo estático:** calculadora de costos (compra + almacenamiento + lucro cesante) que se actualiza al modificar los stocks.
    - **Modelo secuencial de intervalos:** bucle diario de `dias` iteraciones: recibir pedido → demanda → vender → mermar → decidir pedido.
    - **Políticas de reposición:**
        - **(s, Q)** revisión continua: pedir Q cuando la posición de inventario ≤ s.
        - **(R, S)** revisión periódica: cada R días pedir hasta S.
    - **Simulación de demanda:** `N(μ, σ)` con semilla fija para reproducibilidad.
    - **Modelo dinámico continuo:** T(t) = T_base + A·sin(2π·t/30).
    - **Modelo híbrido:** si T(t) > umbral → merma del stock (variable continua afectando el inventario discreto).
    - **Optimización:** barrido de (s,Q) y (R,S) comparando costo total y faltantes.
    """)
