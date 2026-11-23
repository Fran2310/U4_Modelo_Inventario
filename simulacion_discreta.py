"""
==============================================================================
MÓDULO 2: SIMULACIÓN DISCRETA Y POLÍTICAS DE REPOSICIÓN DE INVENTARIO
==============================================================================
Descripción:
    Motor de simulación discreta secuencial día a día para evaluar políticas
    de reposición (s, Q) continua y (R, S) periódica bajo demanda estocástica
    normal N(μ, σ), temperatura dinámica senoidal y merma híbrida por calor.

    Puede importarse desde `main.py` (mediante `render_modulo_simulacion_discreta`)
    o ejecutarse de forma independiente con `streamlit run simulacion_discreta.py`.
==============================================================================
"""

from typing import Dict, Optional
import numpy as np
import pandas as pd


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
    seed: Optional[int] = 42,
) -> pd.DataFrame:
    """
    Simulación discreta secuencial día a día.

    Modelos aplicados:
        - Simulación de demanda estocástica N(μ, σ).
        - Política (s, Q): pedir Q cuando la posición de inventario <= s.
        - Política (R, S): cada R días, pedir hasta alcanzar el nivel S.
        - Temperatura dinámica: T(t) = base + A * sin(2 * pi * t / 30).
        - Merma por calor cuando T(t) > umbral (modelo híbrido).

    La decisión de pedido utiliza la POSICIÓN DE INVENTARIO (stock físico +
    pedidos en tránsito) para evitar pedidos duplicados durante el lead time.
    """
    rng = np.random.default_rng(seed)
    stock = int(prod["Stock Actual"])
    pipeline = []  # [(día_llegada, cantidad)]
    historial = []

    for dia in range(1, dias + 1):
        # 1) Llegada de pedidos pendientes
        recibido = sum(q for d, q in pipeline if d == dia)
        stock += recibido
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
                pedido = int(Q)
        else:  # "RS"
            if dia % R == 0 and posicion < S:
                pedido = int(S - posicion)

        if pedido > 0:
            if lead_time == 0:
                stock += pedido
            else:
                pipeline.append((dia + lead_time, pedido))

        historial.append(
            {
                "Día": dia,
                "Recibido": recibido,
                "Demanda": demanda,
                "Ventas": ventas,
                "Faltantes": faltantes,
                "Temp (°C)": round(float(temp), 2),
                "Merma": merma,
                "Pedido": pedido,
                "Stock Final": stock,
            }
        )

    return pd.DataFrame(historial)


def costos_simulacion(df: pd.DataFrame, prod: pd.Series) -> Dict[str, float]:
    """Convierte el historial diario de simulación en métricas económicas y operativas."""
    c_compra = float(df["Pedido"].sum() * prod["Costo Compra ($)"])
    c_almacen = float(
        df["Stock Final"].mean() * prod["Costo Almacenamiento ($/unidad)"] * len(df)
    )
    c_falt = float(df["Faltantes"].sum() * prod["Margen Unitario ($)"])
    c_merma = float(df["Merma"].sum() * prod["Costo Compra ($)"])
    demanda_total = float(df["Demanda"].sum())
    ventas_total = float(df["Ventas"].sum())
    nivel_servicio = (ventas_total / demanda_total * 100.0) if demanda_total > 0 else 100.0

    return {
        "Costo Compra ($)": c_compra,
        "Costo Almacenamiento ($)": c_almacen,
        "Lucro Cesante ($)": c_falt,
        "Pérdida Merma ($)": c_merma,
        "Costo Total ($)": c_compra + c_almacen + c_falt + c_merma,
        "Faltantes (unid)": int(df["Faltantes"].sum()),
        "Merma (unid)": int(df["Merma"].sum()),
        "Nivel de Servicio (%)": round(nivel_servicio, 2),
    }


# ==============================================================================
# FUNCIONES DE VISUALIZACIÓN (PLOTLY)
# ==============================================================================
def graficar_evolucion_stock(
    df_sq: pd.DataFrame,
    df_rs: pd.DataFrame,
    prod: pd.Series,
    producto_sim: str,
):
    """Genera gráfico comparativo de la evolución diaria del stock para (s,Q) y (R,S)."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_sq["Día"],
            y=df_sq["Stock Final"],
            mode="lines+markers",
            name="Política (s, Q) — Continua",
            line=dict(color="#1f77b4", width=3),
            marker=dict(size=6),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_rs["Día"],
            y=df_rs["Stock Final"],
            mode="lines+markers",
            name="Política (R, S) — Periódica",
            line=dict(color="#ff7f0e", width=3),
            marker=dict(size=6),
        )
    )
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="#d62728",
        annotation_text="Quiebre de stock (0)",
        annotation_position="bottom right",
    )
    fig.add_hline(
        y=float(prod["Stock Mínimo"]),
        line_dash="dot",
        line_color="#e377c2",
        annotation_text=f"Stock mínimo ({int(prod['Stock Mínimo'])})",
        annotation_position="top right",
    )
    fig.update_layout(
        title=f"Evolución Diaria del Stock — {producto_sim}",
        xaxis_title="Día de simulación",
        yaxis_title="Unidades en inventario",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
    )
    return fig


def graficar_temperatura_merma(
    df_sq: pd.DataFrame,
    df_rs: pd.DataFrame,
    temp_umbral: float,
):
    """Genera gráfico combinado de temperatura dinámica y unidades perdidas por merma."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(
            x=df_sq["Día"],
            y=df_sq["Temp (°C)"],
            mode="lines+markers",
            name="Temperatura (°C)",
            line=dict(color="#d62728", width=3),
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df_sq["Día"],
            y=df_sq["Merma"],
            name="Merma (s, Q)",
            marker_color="rgba(31, 119, 180, 0.45)",
        ),
        secondary_y=True,
    )
    fig.add_trace(
        go.Bar(
            x=df_rs["Día"],
            y=df_rs["Merma"],
            name="Merma (R, S)",
            marker_color="rgba(255, 127, 14, 0.45)",
        ),
        secondary_y=True,
    )
    fig.add_hline(
        y=temp_umbral,
        line_dash="dash",
        line_color="#ff9800",
        annotation_text=f"Umbral crítico ({temp_umbral:.1f} °C)",
        secondary_y=False,
    )
    fig.update_layout(
        title="🌡️ Temperatura del Almacén y Merma Híbrida Activada",
        xaxis_title="Día",
        barmode="group",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=360,
    )
    fig.update_yaxes(title_text="Temperatura (°C)", secondary_y=False)
    fig.update_yaxes(title_text="Merma diaria (unidades)", secondary_y=True)
    return fig


def graficar_desglose_costos(cos_sq: Dict[str, float], cos_rs: Dict[str, float]):
    """Genera gráfico de barras agrupadas comparando la estructura de costos por política."""
    import plotly.graph_objects as go

    componentes = [
        "Costo Compra ($)",
        "Costo Almacenamiento ($)",
        "Lucro Cesante ($)",
        "Pérdida Merma ($)",
    ]
    fig = go.Figure(
        data=[
            go.Bar(
                name="Política (s, Q)",
                x=componentes,
                y=[cos_sq[c] for c in componentes],
                marker_color="#1f77b4",
                text=[f"${cos_sq[c]:,.1f}" for c in componentes],
                textposition="auto",
            ),
            go.Bar(
                name="Política (R, S)",
                x=componentes,
                y=[cos_rs[c] for c in componentes],
                marker_color="#ff7f0e",
                text=[f"${cos_rs[c]:,.1f}" for c in componentes],
                textposition="auto",
            ),
        ]
    )
    fig.update_layout(
        title="💰 Desglose Comparativo de Costos por Componente",
        yaxis_title="Monto ($)",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=360,
    )
    return fig


# ==============================================================================
# COMPONENTE INTEGRABLE EN STREAMLIT (PESTAÑA DEL MÓDULO 2)
# ==============================================================================
def render_modulo_simulacion_discreta(df_inventario: pd.DataFrame) -> None:
    """Renderiza el módulo completo de simulación discreta dentro de main.py."""
    import streamlit as st

    st.header("📈 Simulación Discreta — Modelo Secuencial de Intervalos")
    st.caption(
        "Proyección estocástica día a día comparando la política continua (s, Q) "
        "y la política periódica (R, S) con ciclo térmico y merma híbrida."
    )

    lista_productos = df_inventario["Producto"].tolist()

    with st.expander("⚙️ Configurar Parámetros de Simulación Discreta", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            producto_sim = st.selectbox(
                "Producto a simular:", lista_productos, key="sim_prod"
            )
            dias = st.number_input("Horizonte (días):", 10, 120, 30, key="sim_dias")
            lead_time = st.number_input("Lead time (días):", 0, 10, 3, key="sim_lt")
        with c2:
            dem_mean = st.number_input(
                "Demanda media diaria (μ):", 1, 100, 20, key="sim_dm"
            )
            dem_std = st.number_input(
                "Desviación estándar (σ):", 0, 30, 5, key="sim_ds"
            )
            seed_val = st.number_input(
                "Semilla aleatoria:", 0, 9999, 42, key="sim_seed"
            )
        with c3:
            s_val = st.slider("s (punto de reorden):", 0, 150, 60, key="sim_s")
            Q_val = st.slider("Q (lote de pedido):", 10, 300, 100, key="sim_q")
            R_val = st.slider("R (periodo revisión):", 1, 15, 5, key="sim_r")
            S_val = st.slider("S (nivel objetivo):", 50, 400, 160, key="sim_S")
        with c4:
            temp_base = st.slider(
                "Temp. base (°C):", 10.0, 30.0, 20.0, 0.5, key="sim_tb"
            )
            temp_amp = st.slider(
                "Amplitud térmica (°C):", 0.0, 15.0, 8.0, 0.5, key="sim_ta"
            )
            temp_umbral = st.slider(
                "Umbral crítico (°C):", 15.0, 40.0, 26.0, 0.5, key="sim_tu"
            )
            merma_pct = st.slider(
                "Tasa merma por calor:", 0.0, 0.20, 0.03, 0.01, key="sim_mp"
            )

    fila_prod = df_inventario[df_inventario["Producto"] == producto_sim].iloc[0]

    df_sq = simular(
        fila_prod,
        "sQ",
        int(dias),
        int(lead_time),
        float(dem_mean),
        float(dem_std),
        int(s_val),
        int(Q_val),
        int(R_val),
        int(S_val),
        float(temp_base),
        float(temp_amp),
        float(temp_umbral),
        float(merma_pct),
        seed=int(seed_val),
    )
    df_rs = simular(
        fila_prod,
        "RS",
        int(dias),
        int(lead_time),
        float(dem_mean),
        float(dem_std),
        int(s_val),
        int(Q_val),
        int(R_val),
        int(S_val),
        float(temp_base),
        float(temp_amp),
        float(temp_umbral),
        float(merma_pct),
        seed=int(seed_val),
    )

    cos_sq = costos_simulacion(df_sq, fila_prod)
    cos_rs = costos_simulacion(df_rs, fila_prod)

    # Tarjetas comparativas rápidas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Costo Total (s, Q)", f"${cos_sq['Costo Total ($)']:,.2f}")
    m2.metric("Costo Total (R, S)", f"${cos_rs['Costo Total ($)']:,.2f}")
    m3.metric(
        "Nivel de Servicio (s, Q)",
        f"{cos_sq['Nivel de Servicio (%)']:.1f}%",
        delta=f"{cos_sq['Faltantes (unid)']} faltantes",
        delta_color="inverse" if cos_sq["Faltantes (unid)"] > 0 else "normal",
    )
    m4.metric(
        "Nivel de Servicio (R, S)",
        f"{cos_rs['Nivel de Servicio (%)']:.1f}%",
        delta=f"{cos_rs['Faltantes (unid)']} faltantes",
        delta_color="inverse" if cos_rs["Faltantes (unid)"] > 0 else "normal",
    )

    # Gráficas integradas
    st.plotly_chart(
        graficar_evolucion_stock(df_sq, df_rs, fila_prod, producto_sim),
        use_container_width=True,
    )

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(
            graficar_temperatura_merma(df_sq, df_rs, float(temp_umbral)),
            use_container_width=True,
        )
    with col_g2:
        st.plotly_chart(
            graficar_desglose_costos(cos_sq, cos_rs),
            use_container_width=True,
        )

    # Tabla comparativa de costos
    st.subheader("💰 Tabla Comparativa de Costos e Indicadores")
    df_costos = pd.DataFrame(
        [
            {"Política": "(s, Q) Continua", **cos_sq},
            {"Política": "(R, S) Periódica", **cos_rs},
        ]
    ).set_index("Política").T

    st.dataframe(
        df_costos.style.format(
            "${:,.2f}",
            subset=pd.IndexSlice[
                [
                    "Costo Compra ($)",
                    "Costo Almacenamiento ($)",
                    "Lucro Cesante ($)",
                    "Pérdida Merma ($)",
                    "Costo Total ($)",
                ],
                :,
            ],
        ),
        use_container_width=True,
    )

    mejor = "(s, Q)" if cos_sq["Costo Total ($)"] <= cos_rs["Costo Total ($)"] else "(R, S)"
    ahorro = abs(cos_sq["Costo Total ($)"] - cos_rs["Costo Total ($)"])
    st.success(
        f"🏆 **Recomendación:** para **{producto_sim}** con los parámetros actuales, "
        f"la política **{mejor}** logra el menor costo total (ahorro de **${ahorro:,.2f}**)."
    )

    with st.expander(f"📋 Ver detalle diario de la simulación — {producto_sim}"):
        col1, col2 = st.columns(2)
        with col1:
            st.caption("Historial Diario — Política (s, Q)")
            st.dataframe(df_sq, use_container_width=True, hide_index=True)
        with col2:
            st.caption("Historial Diario — Política (R, S)")
            st.dataframe(df_rs, use_container_width=True, hide_index=True)


# ==============================================================================
# EJECUCIÓN INDEPENDIENTE (MODO STANDALONE)
# ==============================================================================
if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(
        page_title="Módulo 2 — Simulación Discreta",
        page_icon="🎲",
        layout="wide",
    )
    datos_demo = pd.DataFrame(
        {
            "Producto": ["Carne", "Lácteos", "Granos", "Higiene"],
            "Precio Venta ($)": [12.50, 4.80, 2.50, 6.20],
            "Costo Compra ($)": [8.20, 2.90, 1.20, 3.40],
            "Margen Unitario ($)": [4.30, 1.90, 1.30, 2.80],
            "Costo Almacenamiento ($/unidad)": [0.65, 0.30, 0.08, 0.15],
            "Stock Actual": [45, 85, 200, 110],
            "Stock Mínimo": [20, 30, 50, 35],
        }
    )
    render_modulo_simulacion_discreta(datos_demo)