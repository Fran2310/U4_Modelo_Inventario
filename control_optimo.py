"""
==============================================================================
MÓDULO 4: EXPERIMENTACIÓN, CONTROL ÓPTIMO Y ANÁLISIS DE SENSIBILIDAD
==============================================================================
Descripción:
    Implementa modelos analíticos y experimentales para la optimización de
    políticas de inventario:
        - Modelo EOQ (Lote Económico de Compra), Stock de Seguridad (SS) y
          Punto de Reorden (ROP) con curva de compensación (Trade-off).
        - Barrido sistemático de parámetros (Grid Search) con restricción de
          nivel de servicio mínimo para políticas (s, Q) y (R, S) y mapas de calor.
        - Experimentación Monte Carlo (múltiples réplicas estocásticas) para
          evaluar robustez, dispersión de costos y nivel de servicio.
        - Análisis de sensibilidad frente a Lead Time, Temperatura Base y
          Volatilidad de Demanda (σ).
        - Evaluación comparativa global para los 4 productos del supermercado.

    Puede importarse desde `main.py` (mediante `render_modulo_control_optimo`)
    o ejecutarse de forma independiente con `streamlit run control_optimo.py`.
==============================================================================
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from simulacion_discreta import costos_simulacion, simular


# Perfiles de demanda diaria de referencia para la comparativa global
DEMANDA_REFERENCIA_PRODUCTOS: Dict[str, Tuple[float, float]] = {
    "Carne": (12.0, 3.0),
    "Lácteos": (22.0, 5.0),
    "Granos": (35.0, 7.0),
    "Higiene": (18.0, 4.0),
}


# ==============================================================================
# 1. MODELO ANALÍTICO EOQ, STOCK DE SEGURIDAD Y CURVA TRADE-OFF
# ==============================================================================
def calcular_eoq(
    demanda_diaria: float,
    costo_orden: float,
    costo_almacen_diario: float,
    lead_time: int,
    dem_std: float,
    nivel_servicio_z: float = 1.645,
    horizonte_dias: int = 30,
) -> Dict[str, float]:
    """
    Calcula el Lote Económico de Compra (EOQ), Stock de Seguridad (SS) y
    Punto de Reorden (ROP) para un horizonte dado.

    Fórmulas:
        - D = demanda_diaria * horizonte_dias
        - H = costo_almacen_diario * horizonte_dias
        - Q* = sqrt((2 * D * K) / H)
        - SS = z * sigma * sqrt(L)
        - ROP = demanda_diaria * L + SS
    """
    demanda_periodo = max(1e-6, demanda_diaria * horizonte_dias)
    costo_almacen_periodo = max(1e-6, costo_almacen_diario * horizonte_dias)

    q_opt = float(np.sqrt((2.0 * demanda_periodo * costo_orden) / costo_almacen_periodo))
    num_pedidos = demanda_periodo / q_opt
    ciclo_dias = q_opt / max(1e-6, demanda_diaria)
    stock_seguridad = float(nivel_servicio_z * dem_std * np.sqrt(max(0, lead_time)))
    rop = float(demanda_diaria * lead_time + stock_seguridad)

    costo_ordenar_total = num_pedidos * costo_orden
    costo_almacen_total = (q_opt / 2.0) * costo_almacen_periodo
    costo_relevante_total = costo_ordenar_total + costo_almacen_total

    return {
        "EOQ (Q*)": round(q_opt, 2),
        "Punto de Reorden (ROP)": round(rop, 2),
        "Stock de Seguridad (SS)": round(stock_seguridad, 2),
        "Pedidos en el periodo": round(num_pedidos, 2),
        "Ciclo entre pedidos (días)": round(ciclo_dias, 2),
        "Costo de Ordenar ($)": round(costo_ordenar_total, 2),
        "Costo de Almacenar ($)": round(costo_almacen_total, 2),
        "Costo Relevante Total ($)": round(costo_relevante_total, 2),
    }


def curva_tradeoff_eoq(
    demanda_diaria: float,
    costo_orden: float,
    costo_almacen_diario: float,
    horizonte_dias: int = 30,
    q_min: float = 15.0,
    q_max: float = 350.0,
    pasos: int = 65,
) -> pd.DataFrame:
    """Genera los puntos de la curva de compensación (ordenar vs. almacenar) en función de Q."""
    demanda_periodo = max(1e-6, demanda_diaria * horizonte_dias)
    costo_almacen_periodo = max(1e-6, costo_almacen_diario * horizonte_dias)
    q_vals = np.linspace(max(5.0, q_min), max(q_min + 10.0, q_max), pasos)

    c_ordenar = (demanda_periodo / q_vals) * costo_orden
    c_almacenar = (q_vals / 2.0) * costo_almacen_periodo
    c_total = c_ordenar + c_almacenar

    return pd.DataFrame(
        {
            "Lote Q": q_vals,
            "Costo de Ordenar ($)": c_ordenar,
            "Costo de Almacenar ($)": c_almacenar,
            "Costo Relevante Total ($)": c_total,
        }
    )


# ==============================================================================
# 2. EXPERIMENTACIÓN: BARRIDO DE PARÁMETROS (GRID SEARCH CON RESTRICCIÓN)
# ==============================================================================
def seleccionar_optimo(df_opt: pd.DataFrame, servicio_minimo: float = 90.0) -> pd.Series:
    """
    Selecciona la configuración de menor costo total que cumpla el nivel de
    servicio mínimo exigido. Si ninguna alcanza el umbral, elige la de mayor
    nivel de servicio y menor costo.
    """
    factibles = df_opt[df_opt["Nivel de Servicio (%)"] >= servicio_minimo]
    if not factibles.empty:
        return factibles.sort_values("Costo Total ($)").iloc[0]
    return df_opt.sort_values(
        by=["Nivel de Servicio (%)", "Costo Total ($)"], ascending=[False, True]
    ).iloc[0]


def barrido_parametros(
    prod: pd.Series,
    dias: int,
    lead_time: int,
    dem_mean: float,
    dem_std: float,
    temp_base: float,
    temp_amp: float,
    temp_umbral: float,
    merma_pct: float,
    s_grid: Optional[List[int]] = None,
    Q_grid: Optional[List[int]] = None,
    R_grid: Optional[List[int]] = None,
    S_grid: Optional[List[int]] = None,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta un barrido de hiperparámetros para las políticas (s, Q) y (R, S)
    evaluando costo total, faltantes, merma y nivel de servicio.
    """
    if s_grid is None:
        s_grid = list(range(20, 161, 20))
    if Q_grid is None:
        Q_grid = list(range(30, 241, 35))
    if R_grid is None:
        R_grid = list(range(1, 10, 2))
    if S_grid is None:
        S_grid = list(range(80, 361, 40))

    res_sq = []
    for s_test in s_grid:
        for q_test in Q_grid:
            df_t = simular(
                prod,
                "sQ",
                dias,
                lead_time,
                dem_mean,
                dem_std,
                s_test,
                q_test,
                5,
                150,
                temp_base,
                temp_amp,
                temp_umbral,
                merma_pct,
                seed=seed,
            )
            c = costos_simulacion(df_t, prod)
            res_sq.append(
                {
                    "Política": "(s, Q)",
                    "s": s_test,
                    "Q": q_test,
                    "Costo Total ($)": c["Costo Total ($)"],
                    "Faltantes (unid)": c["Faltantes (unid)"],
                    "Merma (unid)": c["Merma (unid)"],
                    "Nivel de Servicio (%)": c["Nivel de Servicio (%)"],
                }
            )

    res_rs = []
    for r_test in R_grid:
        for s_obj_test in S_grid:
            df_t = simular(
                prod,
                "RS",
                dias,
                lead_time,
                dem_mean,
                dem_std,
                20,
                50,
                r_test,
                s_obj_test,
                temp_base,
                temp_amp,
                temp_umbral,
                merma_pct,
                seed=seed,
            )
            c = costos_simulacion(df_t, prod)
            res_rs.append(
                {
                    "Política": "(R, S)",
                    "R": r_test,
                    "S": s_obj_test,
                    "Costo Total ($)": c["Costo Total ($)"],
                    "Faltantes (unid)": c["Faltantes (unid)"],
                    "Merma (unid)": c["Merma (unid)"],
                    "Nivel de Servicio (%)": c["Nivel de Servicio (%)"],
                }
            )

    df_sq_opt = pd.DataFrame(res_sq).sort_values("Costo Total ($)").reset_index(drop=True)
    df_rs_opt = pd.DataFrame(res_rs).sort_values("Costo Total ($)").reset_index(drop=True)
    return df_sq_opt, df_rs_opt


# ==============================================================================
# 3. EXPERIMENTACIÓN MONTE CARLO (MÚLTIPLES RÉPLICAS ESTOCÁSTICAS)
# ==============================================================================
def simulacion_monte_carlo(
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
    n_replicas: int = 50,
    seed_base: int = 100,
) -> pd.DataFrame:
    """Ejecuta múltiples réplicas independientes para evaluar robustez estadística."""
    filas = []
    for i in range(n_replicas):
        df_sim = simular(
            prod,
            politica,
            dias,
            lead_time,
            dem_mean,
            dem_std,
            s,
            Q,
            R,
            S,
            temp_base,
            temp_amp,
            temp_umbral,
            merma_pct,
            seed=seed_base + i,
        )
        c = costos_simulacion(df_sim, prod)
        c["Réplica"] = i + 1
        c["Política"] = "(s, Q)" if politica == "sQ" else "(R, S)"
        filas.append(c)
    return pd.DataFrame(filas)


# ==============================================================================
# 4. ANÁLISIS DE SENSIBILIDAD (LEAD TIME, TEMPERATURA Y VOLATILIDAD)
# ==============================================================================
def analisis_sensibilidad_escenarios(
    prod: pd.Series,
    dias: int,
    lead_time_base: int,
    dem_mean: float,
    dem_std_base: float,
    s: int,
    Q: int,
    R: int,
    S: int,
    temp_base_init: float,
    temp_amp: float,
    temp_umbral: float,
    merma_pct: float,
    seed: int = 42,
) -> Dict[str, pd.DataFrame]:
    """Evalúa cómo varía el costo total y el nivel de servicio al perturbar variables clave."""
    filas_lt = []
    for lt in [1, 2, 3, 5, 7]:
        c_sq = costos_simulacion(
            simular(prod, "sQ", dias, lt, dem_mean, dem_std_base, s, Q, R, S, temp_base_init, temp_amp, temp_umbral, merma_pct, seed),
            prod,
        )
        c_rs = costos_simulacion(
            simular(prod, "RS", dias, lt, dem_mean, dem_std_base, s, Q, R, S, temp_base_init, temp_amp, temp_umbral, merma_pct, seed),
            prod,
        )
        filas_lt.append(
            {
                "Lead Time (días)": lt,
                "Costo (s, Q)": c_sq["Costo Total ($)"],
                "Costo (R, S)": c_rs["Costo Total ($)"],
                "Servicio (s, Q) %": c_sq["Nivel de Servicio (%)"],
                "Servicio (R, S) %": c_rs["Nivel de Servicio (%)"],
            }
        )

    filas_temp = []
    for tb in [14.0, 18.0, 22.0, 26.0, 30.0]:
        c_sq = costos_simulacion(
            simular(prod, "sQ", dias, lead_time_base, dem_mean, dem_std_base, s, Q, R, S, tb, temp_amp, temp_umbral, merma_pct, seed),
            prod,
        )
        c_rs = costos_simulacion(
            simular(prod, "RS", dias, lead_time_base, dem_mean, dem_std_base, s, Q, R, S, tb, temp_amp, temp_umbral, merma_pct, seed),
            prod,
        )
        filas_temp.append(
            {
                "Temp. Base (°C)": tb,
                "Costo (s, Q)": c_sq["Costo Total ($)"],
                "Costo (R, S)": c_rs["Costo Total ($)"],
                "Merma (s, Q)": c_sq["Merma (unid)"],
                "Merma (R, S)": c_rs["Merma (unid)"],
            }
        )

    filas_std = []
    for std_val in [2.0, 5.0, 8.0, 12.0, 16.0]:
        c_sq = costos_simulacion(
            simular(prod, "sQ", dias, lead_time_base, dem_mean, std_val, s, Q, R, S, temp_base_init, temp_amp, temp_umbral, merma_pct, seed),
            prod,
        )
        c_rs = costos_simulacion(
            simular(prod, "RS", dias, lead_time_base, dem_mean, std_val, s, Q, R, S, temp_base_init, temp_amp, temp_umbral, merma_pct, seed),
            prod,
        )
        filas_std.append(
            {
                "Desviación Demanda (σ)": std_val,
                "Costo (s, Q)": c_sq["Costo Total ($)"],
                "Costo (R, S)": c_rs["Costo Total ($)"],
                "Faltantes (s, Q)": c_sq["Faltantes (unid)"],
                "Faltantes (R, S)": c_rs["Faltantes (unid)"],
            }
        )

    return {
        "lead_time": pd.DataFrame(filas_lt),
        "temperatura": pd.DataFrame(filas_temp),
        "volatilidad": pd.DataFrame(filas_std),
    }


def evaluar_todos_los_productos(
    df_inventario: pd.DataFrame,
    dias: int = 30,
    lead_time: int = 3,
    costo_orden: float = 25.0,
    temp_base: float = 20.0,
    temp_amp: float = 8.0,
    temp_umbral: float = 26.0,
    merma_pct: float = 0.03,
    servicio_minimo: float = 95.0,
) -> pd.DataFrame:
    """Ejecuta optimización comparativa con restricción de servicio para los 4 productos."""
    resumen = []
    for _, fila in df_inventario.iterrows():
        nombre = str(fila["Producto"])
        dem_m, dem_s = DEMANDA_REFERENCIA_PRODUCTOS.get(nombre, (20.0, 5.0))
        eoq = calcular_eoq(
            dem_m,
            costo_orden,
            float(fila["Costo Almacenamiento ($/unidad)"]),
            lead_time,
            dem_s,
            horizonte_dias=dias,
        )
        df_sq_opt, df_rs_opt = barrido_parametros(
            fila,
            dias,
            lead_time,
            dem_m,
            dem_s,
            temp_base,
            temp_amp,
            temp_umbral,
            merma_pct,
        )
        top_sq = seleccionar_optimo(df_sq_opt, servicio_minimo)
        top_rs = seleccionar_optimo(df_rs_opt, servicio_minimo)
        mejor_pol = "(s, Q)" if top_sq["Costo Total ($)"] <= top_rs["Costo Total ($)"] else "(R, S)"
        ahorro = abs(float(top_sq["Costo Total ($)"] - top_rs["Costo Total ($)"]))

        resumen.append(
            {
                "Producto": nombre,
                "Demanda μ±σ": f"{dem_m:.0f} ± {dem_s:.0f}",
                "EOQ (Q*)": int(round(eoq["EOQ (Q*)"])),
                "ROP Analítico": int(round(eoq["Punto de Reorden (ROP)"])),
                "Óptimo (s, Q)": f"s={int(top_sq['s'])}, Q={int(top_sq['Q'])}",
                "Costo (s, Q) ($)": round(float(top_sq["Costo Total ($)"]), 2),
                "Servicio (s, Q) %": float(top_sq["Nivel de Servicio (%)"]),
                "Óptimo (R, S)": f"R={int(top_rs['R'])}, S={int(top_rs['S'])}",
                "Costo (R, S) ($)": round(float(top_rs["Costo Total ($)"]), 2),
                "Servicio (R, S) %": float(top_rs["Nivel de Servicio (%)"]),
                "Mejor Política": mejor_pol,
                "Ahorro ($)": round(ahorro, 2),
            }
        )
    return pd.DataFrame(resumen)


# ==============================================================================
# 5. VISUALIZACIONES PLOTLY
# ==============================================================================
def graficar_tradeoff_eoq(df_curve: pd.DataFrame, eoq_info: Dict[str, float]):
    """Gráfica clásica de compensación (Trade-off) entre costo de ordenar y almacenar."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_curve["Lote Q"],
            y=df_curve["Costo de Ordenar ($)"],
            mode="lines",
            name="Costo de Ordenar",
            line=dict(color="#1f77b4", width=2.5, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_curve["Lote Q"],
            y=df_curve["Costo de Almacenar ($)"],
            mode="lines",
            name="Costo de Almacenamiento",
            line=dict(color="#ff7f0e", width=2.5, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_curve["Lote Q"],
            y=df_curve["Costo Relevante Total ($)"],
            mode="lines",
            name="Costo Relevante Total",
            line=dict(color="#2ca02c", width=3.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[eoq_info["EOQ (Q*)"]],
            y=[eoq_info["Costo Relevante Total ($)"]],
            mode="markers+text",
            name="Óptimo EOQ (Q*)",
            marker=dict(color="#d62728", size=12, symbol="star"),
            text=[f"Q* = {eoq_info['EOQ (Q*)']:.0f}"],
            textposition="top center",
        )
    )
    fig.update_layout(
        title="⚖️ Curva de Compensación (Trade-Off) del Modelo EOQ",
        xaxis_title="Tamaño del lote de pedido (Q)",
        yaxis_title="Costo del periodo ($)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=390,
    )
    return fig


def graficar_heatmap_optimizacion(
    df_opt: pd.DataFrame,
    x_col: str,
    y_col: str,
    titulo: str,
    optimo: Optional[pd.Series] = None,
):
    """Mapa de calor del Costo Total sobre la malla de parámetros evaluados."""
    import plotly.graph_objects as go

    pivote = df_opt.pivot(index=y_col, columns=x_col, values="Costo Total ($)")
    top = optimo if optimo is not None else df_opt.iloc[0]

    fig = go.Figure(
        data=go.Heatmap(
            z=pivote.values,
            x=[str(c) for c in pivote.columns],
            y=[str(r) for r in pivote.index],
            colorscale="Viridis_r",
            colorbar=dict(title="Costo ($)"),
            hovertemplate=f"{x_col}=%{{x}}<br>{y_col}=%{{y}}<br>Costo Total=$%{{z:,.2f}}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[str(int(top[x_col]))],
            y=[str(int(top[y_col]))],
            mode="markers+text",
            name="Óptimo Factible",
            marker=dict(color="#ff4b4b", size=14, symbol="star"),
            text=[f"Óptimo (${top['Costo Total ($)']:,.0f})"],
            textposition="top center",
            textfont=dict(color="white", size=11),
        )
    )
    fig.update_layout(
        title=titulo,
        xaxis_title=x_col,
        yaxis_title=y_col,
        height=390,
    )
    return fig


def graficar_monte_carlo(df_mc_sq: pd.DataFrame, df_mc_rs: pd.DataFrame):
    """Histograma superpuesto de la distribución de costos totales en Monte Carlo."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=df_mc_sq["Costo Total ($)"],
            name="Política (s, Q)",
            opacity=0.65,
            marker_color="#1f77b4",
            nbinsx=20,
        )
    )
    fig.add_trace(
        go.Histogram(
            x=df_mc_rs["Costo Total ($)"],
            name="Política (R, S)",
            opacity=0.65,
            marker_color="#ff7f0e",
            nbinsx=20,
        )
    )
    fig.update_layout(
        title="🎲 Distribución de Costos Totales — Simulación Monte Carlo",
        xaxis_title="Costo Total ($)",
        yaxis_title="Frecuencia (réplicas)",
        barmode="overlay",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=370,
    )
    return fig


def graficar_sensibilidad(
    df_sens: pd.DataFrame,
    x_col: str,
    titulo: str,
    x_label: str,
):
    """Curva de sensibilidad del costo total para (s, Q) y (R, S)."""
    import plotly.graph_objects as go

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_sens[x_col],
            y=df_sens["Costo (s, Q)"],
            mode="lines+markers",
            name="Política (s, Q)",
            line=dict(color="#1f77b4", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_sens[x_col],
            y=df_sens["Costo (R, S)"],
            mode="lines+markers",
            name="Política (R, S)",
            line=dict(color="#ff7f0e", width=3),
        )
    )
    fig.update_layout(
        title=titulo,
        xaxis_title=x_label,
        yaxis_title="Costo Total ($)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=340,
    )
    return fig


def graficar_comparativa_productos(df_resumen: pd.DataFrame):
    """Gráfica de barras agrupadas con el costo óptimo por producto entre (s, Q) y (R, S)."""
    import plotly.graph_objects as go

    fig = go.Figure(
        data=[
            go.Bar(
                name="Óptimo (s, Q)",
                x=df_resumen["Producto"],
                y=df_resumen["Costo (s, Q) ($)"],
                marker_color="#1f77b4",
                text=[f"${v:,.0f}" for v in df_resumen["Costo (s, Q) ($)"]],
                textposition="auto",
            ),
            go.Bar(
                name="Óptimo (R, S)",
                x=df_resumen["Producto"],
                y=df_resumen["Costo (R, S) ($)"],
                marker_color="#ff7f0e",
                text=[f"${v:,.0f}" for v in df_resumen["Costo (R, S) ($)"]],
                textposition="auto",
            ),
        ]
    )
    fig.update_layout(
        title="🛒 Comparativa Global de Costo Óptimo por Producto (30 días)",
        xaxis_title="Categoría de Producto",
        yaxis_title="Costo Total Óptimo ($)",
        barmode="group",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    )
    return fig


# ==============================================================================
# 6. COMPONENTE INTEGRABLE EN STREAMLIT (PESTAÑA DEL MÓDULO 4)
# ==============================================================================
def render_modulo_control_optimo(df_inventario: pd.DataFrame) -> None:
    """Renderiza el Módulo 4 completo dentro de main.py."""
    import streamlit as st

    st.header("🔬 Experimentación, Control Óptimo y Análisis de Sensibilidad")
    st.caption(
        "Cálculo analítico EOQ/ROP, optimización restringida por nivel de servicio "
        "con mapas de calor, validación Monte Carlo y sensibilidad operativa."
    )

    lista_productos = df_inventario["Producto"].tolist()

    with st.expander("⚙️ Parámetros del Experimento de Optimización", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            prod_opt = st.selectbox("Producto objetivo:", lista_productos, key="opt_prod")
            dias_opt = st.number_input("Horizonte (días):", 15, 90, 30, key="opt_dias")
            lt_opt = st.number_input("Lead time (días):", 1, 10, 3, key="opt_lt")
        with c2:
            dem_def, std_def = DEMANDA_REFERENCIA_PRODUCTOS.get(prod_opt, (20.0, 5.0))
            dem_m = st.number_input(
                "Demanda media diaria (μ):",
                min_value=1.0,
                max_value=120.0,
                value=float(dem_def),
                step=1.0,
                key=f"opt_dm_{prod_opt}",
            )
            dem_s = st.number_input(
                "Desviación estándar (σ):",
                min_value=0.0,
                max_value=40.0,
                value=float(std_def),
                step=1.0,
                key=f"opt_ds_{prod_opt}",
            )
            servicio_min = st.slider(
                "Nivel de servicio mínimo exigido (%):",
                min_value=80.0,
                max_value=100.0,
                value=95.0,
                step=1.0,
                key="opt_serv_min",
                help="Evita soluciones degeneradas que reducen compras a costa de desabastecer la tienda.",
            )
        with c3:
            costo_orden = st.number_input(
                "Costo fijo por orden K ($):",
                min_value=5.0,
                max_value=200.0,
                value=25.0,
                step=5.0,
                key="opt_k",
            )
            nivel_serv = st.selectbox(
                "Nivel de servicio objetivo (EOQ):",
                options=[("90% (z=1.28)", 1.282), ("95% (z=1.645)", 1.645), ("99% (z=2.326)", 2.326)],
                index=1,
                format_func=lambda x: x[0],
                key="opt_z",
            )
            n_replicas = st.slider("Réplicas Monte Carlo:", 20, 150, 50, 10, key="opt_mc_n")
        with c4:
            temp_base = st.slider("Temp. base (°C):", 12.0, 30.0, 20.0, 0.5, key="opt_tb")
            temp_amp = st.slider("Amplitud térmica (°C):", 0.0, 15.0, 8.0, 0.5, key="opt_ta")
            temp_umbral = st.slider("Umbral crítico (°C):", 18.0, 38.0, 26.0, 0.5, key="opt_tu")
            merma_pct = st.slider("Tasa merma calor:", 0.0, 0.15, 0.03, 0.01, key="opt_mp")

    fila_prod = df_inventario[df_inventario["Producto"] == prod_opt].iloc[0]

    sub_eoq, sub_grid, sub_mc, sub_global = st.tabs(
        [
            "📐 Modelo Analítico EOQ",
            "🗺️ Optimización y Mapas de Calor",
            "🎲 Monte Carlo y Sensibilidad",
            "🛒 Comparativa Global (4 Productos)",
        ]
    )

    # --- SUBPESTAÑA 1: EOQ Y TRADE-OFF ---
    with sub_eoq:
        eoq = calcular_eoq(
            float(dem_m),
            float(costo_orden),
            float(fila_prod["Costo Almacenamiento ($/unidad)"]),
            int(lt_opt),
            float(dem_s),
            nivel_servicio_z=float(nivel_serv[1]),
            horizonte_dias=int(dias_opt),
        )
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Lote Económico (Q*)", f"{eoq['EOQ (Q*)']:.0f} unid.")
        k2.metric("Punto de Reorden (ROP)", f"{eoq['Punto de Reorden (ROP)']:.0f} unid.")
        k3.metric("Stock de Seguridad (SS)", f"{eoq['Stock de Seguridad (SS)']:.0f} unid.")
        k4.metric("Ciclo Óptimo", f"{eoq['Ciclo entre pedidos (días)']:.1f} días")

        q_max_curve = max(250.0, eoq["EOQ (Q*)"] * 2.4)
        df_curve = curva_tradeoff_eoq(
            float(dem_m),
            float(costo_orden),
            float(fila_prod["Costo Almacenamiento ($/unidad)"]),
            int(dias_opt),
            q_min=max(10.0, eoq["EOQ (Q*)"] * 0.25),
            q_max=q_max_curve,
        )
        st.plotly_chart(graficar_tradeoff_eoq(df_curve, eoq), use_container_width=True)

    # --- SUBPESTAÑA 2: BARRIDO DE PARÁMETROS Y MAPAS DE CALOR ---
    df_sq_opt, df_rs_opt = barrido_parametros(
        fila_prod,
        int(dias_opt),
        int(lt_opt),
        float(dem_m),
        float(dem_s),
        float(temp_base),
        float(temp_amp),
        float(temp_umbral),
        float(merma_pct),
    )
    top_sq = seleccionar_optimo(df_sq_opt, float(servicio_min))
    top_rs = seleccionar_optimo(df_rs_opt, float(servicio_min))

    with sub_grid:
        c_hm1, c_hm2 = st.columns(2)
        with c_hm1:
            st.plotly_chart(
                graficar_heatmap_optimizacion(
                    df_sq_opt, "s", "Q", f"Mapa de Calor — Política (s, Q) [{prod_opt}]", top_sq
                ),
                use_container_width=True,
            )
            st.info(
                f"🥇 **Óptimo (s, Q) con servicio ≥ {servicio_min:.0f}%:** "
                f"s = {int(top_sq['s'])}, Q = {int(top_sq['Q'])} → "
                f"**${top_sq['Costo Total ($)']:,.2f}** | Servicio: **{top_sq['Nivel de Servicio (%)']:.1f}%**"
            )
        with c_hm2:
            st.plotly_chart(
                graficar_heatmap_optimizacion(
                    df_rs_opt, "R", "S", f"Mapa de Calor — Política (R, S) [{prod_opt}]", top_rs
                ),
                use_container_width=True,
            )
            st.info(
                f"🥇 **Óptimo (R, S) con servicio ≥ {servicio_min:.0f}%:** "
                f"R = {int(top_rs['R'])}, S = {int(top_rs['S'])} → "
                f"**${top_rs['Costo Total ($)']:,.2f}** | Servicio: **{top_rs['Nivel de Servicio (%)']:.1f}%**"
            )

        with st.expander("📋 Ver Top 10 configuraciones factibles por política"):
            t1, t2 = st.columns(2)
            with t1:
                st.caption(f"Top 10 — (s, Q) con servicio ≥ {servicio_min:.0f}%")
                df_sq_f = df_sq_opt[df_sq_opt["Nivel de Servicio (%)"] >= servicio_min]
                st.dataframe(
                    (df_sq_f if not df_sq_f.empty else df_sq_opt).head(10).style.format({"Costo Total ($)": "${:,.2f}"}),
                    use_container_width=True,
                    hide_index=True,
                )
            with t2:
                st.caption(f"Top 10 — (R, S) con servicio ≥ {servicio_min:.0f}%")
                df_rs_f = df_rs_opt[df_rs_opt["Nivel de Servicio (%)"] >= servicio_min]
                st.dataframe(
                    (df_rs_f if not df_rs_f.empty else df_rs_opt).head(10).style.format({"Costo Total ($)": "${:,.2f}"}),
                    use_container_width=True,
                    hide_index=True,
                )

    # --- SUBPESTAÑA 3: MONTE CARLO Y ANÁLISIS DE SENSIBILIDAD ---
    with sub_mc:
        st.caption(
            f"Validando las políticas óptimas halladas: (s={int(top_sq['s'])}, Q={int(top_sq['Q'])}) "
            f"vs. (R={int(top_rs['R'])}, S={int(top_rs['S'])}) en {n_replicas} réplicas independientes."
        )
        df_mc_sq = simulacion_monte_carlo(
            fila_prod, "sQ", int(dias_opt), int(lt_opt), float(dem_m), float(dem_s),
            int(top_sq["s"]), int(top_sq["Q"]), int(top_rs["R"]), int(top_rs["S"]),
            float(temp_base), float(temp_amp), float(temp_umbral), float(merma_pct),
            n_replicas=int(n_replicas),
        )
        df_mc_rs = simulacion_monte_carlo(
            fila_prod, "RS", int(dias_opt), int(lt_opt), float(dem_m), float(dem_s),
            int(top_sq["s"]), int(top_sq["Q"]), int(top_rs["R"]), int(top_rs["S"]),
            float(temp_base), float(temp_amp), float(temp_umbral), float(merma_pct),
            n_replicas=int(n_replicas),
        )

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric(
            "Media Costo (s, Q)",
            f"${df_mc_sq['Costo Total ($)'].mean():,.2f}",
            delta=f"±${df_mc_sq['Costo Total ($)'].std():,.2f}",
            delta_color="off",
        )
        mc2.metric(
            "Media Costo (R, S)",
            f"${df_mc_rs['Costo Total ($)'].mean():,.2f}",
            delta=f"±${df_mc_rs['Costo Total ($)'].std():,.2f}",
            delta_color="off",
        )
        mc3.metric("Servicio Promedio (s, Q)", f"{df_mc_sq['Nivel de Servicio (%)'].mean():.2f}%")
        mc4.metric("Servicio Promedio (R, S)", f"{df_mc_rs['Nivel de Servicio (%)'].mean():.2f}%")

        st.plotly_chart(graficar_monte_carlo(df_mc_sq, df_mc_rs), use_container_width=True)

        sens = analisis_sensibilidad_escenarios(
            fila_prod, int(dias_opt), int(lt_opt), float(dem_m), float(dem_s),
            int(top_sq["s"]), int(top_sq["Q"]), int(top_rs["R"]), int(top_rs["S"]),
            float(temp_base), float(temp_amp), float(temp_umbral), float(merma_pct),
        )
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.plotly_chart(
                graficar_sensibilidad(
                    sens["lead_time"], "Lead Time (días)", "Sensibilidad al Lead Time", "Lead Time (días)"
                ),
                use_container_width=True,
            )
        with sc2:
            st.plotly_chart(
                graficar_sensibilidad(
                    sens["temperatura"], "Temp. Base (°C)", "Sensibilidad a la Temperatura", "Temperatura Base (°C)"
                ),
                use_container_width=True,
            )
        with sc3:
            st.plotly_chart(
                graficar_sensibilidad(
                    sens["volatilidad"], "Desviación Demanda (σ)", "Sensibilidad a la Volatilidad", "Desviación σ (unid/día)"
                ),
                use_container_width=True,
            )

    # --- SUBPESTAÑA 4: COMPARATIVA GLOBAL DE LOS 4 PRODUCTOS ---
    with sub_global:
        df_resumen = evaluar_todos_los_productos(
            df_inventario,
            dias=int(dias_opt),
            lead_time=int(lt_opt),
            costo_orden=float(costo_orden),
            temp_base=float(temp_base),
            temp_amp=float(temp_amp),
            temp_umbral=float(temp_umbral),
            merma_pct=float(merma_pct),
            servicio_minimo=float(servicio_min),
        )
        st.plotly_chart(graficar_comparativa_productos(df_resumen), use_container_width=True)
        st.dataframe(
            df_resumen.style.format(
                {
                    "Costo (s, Q) ($)": "${:,.2f}",
                    "Costo (R, S) ($)": "${:,.2f}",
                    "Ahorro ($)": "${:,.2f}",
                    "Servicio (s, Q) %": "{:.1f}%",
                    "Servicio (R, S) %": "{:.1f}%",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ==============================================================================
# 7. EJECUCIÓN INDEPENDIENTE (MODO STANDALONE)
# ==============================================================================
if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(
        page_title="Módulo 4 — Experimentación y Control Óptimo",
        page_icon="🔬",
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
    render_modulo_control_optimo(datos_demo)