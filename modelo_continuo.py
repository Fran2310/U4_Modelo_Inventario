"""
==============================================================================
MÓDULO 3: MODELADO CONTINUO DE MERMAS Y DEGRADACIÓN (EDO)
==============================================================================
Descripción:
    Modelado continuo de la degradación física de productos perecederos
    mediante Ecuaciones Diferenciales Ordinarias (EDO) dependientes de la
    temperatura ambiental, resueltas por Euler Explícito, Runge-Kutta 4 (RK4)
    y SciPy RK45 adaptativo.

    Puede importarse desde `main.py` (mediante `render_modulo_continuo`) o
    ejecutarse de forma independiente con `streamlit run modelo_continuo.py`.
==============================================================================
"""

from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp


# ==============================================================================
# 1. DICCIONARIO OFICIAL DE LOS 4 PRODUCTOS
# ==============================================================================
PRODUCTOS_PERECEDEROS: Dict[str, Dict[str, float | bool]] = {
    "Carne": {
        "s0_default": 800.0,
        "lambda_0": 0.035,
        "sensibilidad_temp": 0.12,
        "temp_optima": 4.0,
        "perecedero": True,
    },
    "Lácteos": {
        "s0_default": 1200.0,
        "lambda_0": 0.020,
        "sensibilidad_temp": 0.09,
        "temp_optima": 6.0,
        "perecedero": True,
    },
    "Granos": {
        "s0_default": 2500.0,
        "lambda_0": 0.002,
        "sensibilidad_temp": 0.01,
        "temp_optima": 20.0,
        "perecedero": False,
    },
    "Higiene": {
        "s0_default": 1500.0,
        "lambda_0": 0.0,
        "sensibilidad_temp": 0.0,
        "temp_optima": 25.0,
        "perecedero": False,
    },
}


# ==============================================================================
# 2. FUNCIÓN DE TASA DE CAMBIO (EDO BASE)
# ==============================================================================
def tasa_degradacion(
    t: float,
    S: float,
    lambda_base: float,
    temp_amb: float,
    props: Dict[str, float | bool],
) -> float:
    """Calcula la derivada dS/dt según la temperatura y sensibilidad del producto."""
    if not props["perecedero"] or S <= 0:
        return 0.0
    delta_temp = max(0.0, temp_amb - float(props["temp_optima"]))
    factor_temp = float(np.exp(float(props["sensibilidad_temp"]) * delta_temp))
    return -(lambda_base * factor_temp) * S


# ==============================================================================
# 3. MÉTODOS NUMÉRICOS DE APROXIMACIÓN
# ==============================================================================
def resolver_euler(
    s0: float,
    lambda_base: float,
    temp_amb: float,
    props: Dict[str, float | bool],
    t_max: float = 30.0,
    n_pasos: int = 300,
) -> Tuple[np.ndarray, np.ndarray]:
    """Método de Euler Explícito (primer orden) con paso configurable."""
    t = np.linspace(0, t_max, n_pasos)
    dt = t[1] - t[0]
    y = np.zeros(n_pasos)
    y[0] = s0
    for i in range(n_pasos - 1):
        dy = tasa_degradacion(t[i], y[i], lambda_base, temp_amb, props)
        y[i + 1] = max(0.0, y[i] + dt * dy)
    return t, y


def resolver_rk4(
    s0: float,
    lambda_base: float,
    temp_amb: float,
    props: Dict[str, float | bool],
    t_max: float = 30.0,
    n_pasos: int = 300,
) -> Tuple[np.ndarray, np.ndarray]:
    """Método clásico de Runge-Kutta de 4to Orden (RK4) con paso configurable."""
    t = np.linspace(0, t_max, n_pasos)
    dt = t[1] - t[0]
    y = np.zeros(n_pasos)
    y[0] = s0
    for i in range(n_pasos - 1):
        ti, yi = t[i], y[i]
        k1 = tasa_degradacion(ti, yi, lambda_base, temp_amb, props)
        k2 = tasa_degradacion(ti + 0.5 * dt, yi + 0.5 * dt * k1, lambda_base, temp_amb, props)
        k3 = tasa_degradacion(ti + 0.5 * dt, yi + 0.5 * dt * k2, lambda_base, temp_amb, props)
        k4 = tasa_degradacion(ti + dt, yi + dt * k3, lambda_base, temp_amb, props)
        y[i + 1] = max(0.0, yi + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4))
    return t, y


def resolver_scipy(
    s0: float,
    lambda_base: float,
    temp_amb: float,
    props: Dict[str, float | bool],
    t_max: float = 30.0,
    n_puntos: int = 300,
) -> Tuple[np.ndarray, np.ndarray]:
    """Método adaptativo Dormand-Prince (Runge-Kutta 4(5)) vía SciPy."""
    t_eval = np.linspace(0, t_max, n_puntos)
    if not props["perecedero"]:
        return t_eval, np.full_like(t_eval, s0, dtype=float)

    def sistema(t: float, y: np.ndarray) -> List[float]:
        return [tasa_degradacion(t, float(y[0]), lambda_base, temp_amb, props)]

    sol = solve_ivp(fun=sistema, t_span=(0, t_max), y0=[s0], t_eval=t_eval, rtol=1e-8, atol=1e-10)
    return sol.t, np.maximum(0.0, sol.y[0])


def resolver_modelo_continuo(
    nombre_producto: str,
    s0: float,
    lambda_base: float,
    temp_amb: float,
    t_max: float = 30.0,
    metodo: str = "Runge-Kutta 4 (RK4)",
    n_pasos: int = 300,
) -> Tuple[np.ndarray, np.ndarray]:
    """Función envoltorio principal para seleccionar el integrador numérico."""
    props = PRODUCTOS_PERECEDEROS.get(nombre_producto, PRODUCTOS_PERECEDEROS["Carne"])

    if metodo == "Euler Explícito":
        return resolver_euler(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    if metodo == "Runge-Kutta 4 (RK4)":
        return resolver_rk4(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    return resolver_scipy(s0, lambda_base, temp_amb, props, t_max, n_pasos)


def comparar_metodos_numericos(
    nombre_producto: str,
    s0: float,
    lambda_base: float,
    temp_amb: float,
    t_max: float = 30.0,
    n_pasos: int = 150,
) -> Dict[str, object]:
    """Compara Euler Explícito, RK4 y SciPy RK45 midiendo error absoluto contra la solución analítica."""
    props = PRODUCTOS_PERECEDEROS.get(nombre_producto, PRODUCTOS_PERECEDEROS["Carne"])
    t_eu, y_eu = resolver_euler(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    t_rk, y_rk = resolver_rk4(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    t_sp, y_sp = resolver_scipy(s0, lambda_base, temp_amb, props, t_max, n_pasos)

    # Solución analítica exacta: S(t) = S0 * exp(-lambda_eff * t)
    if props["perecedero"]:
        delta_temp = max(0.0, temp_amb - float(props["temp_optima"]))
        lambda_eff = lambda_base * float(np.exp(float(props["sensibilidad_temp"]) * delta_temp))
        y_exact = s0 * np.exp(-lambda_eff * t_eu)
    else:
        y_exact = np.full_like(t_eu, s0, dtype=float)

    tabla_error = pd.DataFrame(
        [
            {
                "Método": "Euler Explícito",
                "Stock Final (unid)": round(float(y_eu[-1]), 3),
                "Merma Total (unid)": round(float(s0 - y_eu[-1]), 3),
                "Error Máx vs. Exacta": round(float(np.max(np.abs(y_eu - y_exact))), 5),
                "MAE vs. Exacta": round(float(np.mean(np.abs(y_eu - y_exact))), 5),
            },
            {
                "Método": "Runge-Kutta 4 (RK4)",
                "Stock Final (unid)": round(float(y_rk[-1]), 3),
                "Merma Total (unid)": round(float(s0 - y_rk[-1]), 3),
                "Error Máx vs. Exacta": round(float(np.max(np.abs(y_rk - y_exact))), 5),
                "MAE vs. Exacta": round(float(np.mean(np.abs(y_rk - y_exact))), 5),
            },
            {
                "Método": "SciPy (RK45 Adaptativo)",
                "Stock Final (unid)": round(float(y_sp[-1]), 3),
                "Merma Total (unid)": round(float(s0 - y_sp[-1]), 3),
                "Error Máx vs. Exacta": round(float(np.max(np.abs(y_sp - y_exact))), 5),
                "MAE vs. Exacta": round(float(np.mean(np.abs(y_sp - y_exact))), 5),
            },
        ]
    )

    return {
        "t": t_eu,
        "euler": y_eu,
        "rk4": y_rk,
        "scipy": y_sp,
        "exacta": y_exact,
        "tabla_error": tabla_error,
    }


def curvas_sensibilidad_temperatura(
    nombre_producto: str,
    s0: float,
    lambda_base: float,
    temperaturas: Optional[List[float]] = None,
    t_max: float = 30.0,
    n_pasos: int = 150,
) -> Dict[float, Tuple[np.ndarray, np.ndarray]]:
    """Evalúa la curva de degradación continua para múltiples temperaturas ambientales."""
    if temperaturas is None:
        temperaturas = [4.0, 10.0, 18.0, 25.0, 32.0]
    resultados = {}
    for temp in temperaturas:
        resultados[temp] = resolver_modelo_continuo(
            nombre_producto, s0, lambda_base, temp, t_max, "Runge-Kutta 4 (RK4)", n_pasos
        )
    return resultados


# ==============================================================================
# 4. VISUALIZACIONES PLOTLY
# ==============================================================================
def graficar_comparativa_metodos(
    comp: Dict[str, object],
    prod_key: str,
    metodo_seleccionado: str,
    n_pasos: int,
    mostrar_todos: bool = True,
):
    """Genera gráfico Plotly de la evolución continua del inventario y comparación de integradores."""
    import plotly.graph_objects as go

    t = comp["t"]
    fig = go.Figure()

    if mostrar_todos:
        fig.add_trace(
            go.Scatter(
                x=t,
                y=comp["euler"],
                mode="lines+markers" if n_pasos < 35 else "lines",
                name="Euler Explícito",
                line=dict(color="#ef553b", width=2, dash="dot"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=t,
                y=comp["rk4"],
                mode="lines+markers" if n_pasos < 35 else "lines",
                name="Runge-Kutta 4 (RK4)",
                line=dict(color="#00cc96", width=3),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=t,
                y=comp["scipy"],
                mode="lines",
                name="SciPy RK45 (Referencia)",
                line=dict(color="#636efa", width=2, dash="dash"),
            )
        )
        titulo = f"Comparativa de Métodos Numéricos — {prod_key} (N = {n_pasos} pasos)"
    else:
        clave = {
            "Euler Explícito": "euler",
            "Runge-Kutta 4 (RK4)": "rk4",
            "SciPy (RK45 Adaptativo)": "scipy",
        }[metodo_seleccionado]
        fig.add_trace(
            go.Scatter(
                x=t,
                y=comp[clave],
                mode="lines+markers" if n_pasos < 40 else "lines",
                name=f"{prod_key} ({metodo_seleccionado})",
                line=dict(color="#ffa15a", width=3),
            )
        )
        titulo = f"Evolución del Inventario Continuo — {prod_key} ({metodo_seleccionado})"

    fig.update_layout(
        title=titulo,
        xaxis_title="Tiempo (Días)",
        yaxis_title="Unidades físicas disponibles",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
    )
    return fig


def graficar_sensibilidad_termica(
    curvas_temp: Dict[float, Tuple[np.ndarray, np.ndarray]],
    prod_key: str,
):
    """Genera gráfico de sensibilidad de la degradación ante distintas temperaturas."""
    import plotly.graph_objects as go

    paleta = ["#1f77b4", "#17becf", "#2ca02c", "#ff7f0e", "#d62728"]
    fig = go.Figure()
    for idx, (temp, (t_vals, s_vals)) in enumerate(curvas_temp.items()):
        fig.add_trace(
            go.Scatter(
                x=t_vals,
                y=s_vals,
                mode="lines",
                name=f"{temp:.0f} °C",
                line=dict(color=paleta[idx % len(paleta)], width=2.5),
            )
        )
    fig.update_layout(
        title=f"🌡️ Sensibilidad Térmica de Degradación — {prod_key}",
        xaxis_title="Tiempo (Días)",
        yaxis_title="Stock remanente (unidades)",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
    )
    return fig


# ==============================================================================
# 5. COMPONENTE INTEGRABLE EN STREAMLIT (PESTAÑA DEL MÓDULO 3)
# ==============================================================================
def render_modulo_continuo(df_inventario: Optional[pd.DataFrame] = None) -> None:
    """Renderiza el Módulo 3 (EDO continua) dentro de main.py."""
    import streamlit as st

    st.header("🧪 Modelo Continuo y Dinámica de Perecederos (EDO)")
    st.caption(
        "Resolución numérica de dS/dt = -λ(T)·S para evaluar la merma física continua "
        "y comparar precisión entre Euler Explícito, RK4 y SciPy RK45."
    )

    with st.expander("⚙️ Configurar Parámetros del Modelo Continuo", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            prod_key = st.selectbox(
                "Producto:", list(PRODUCTOS_PERECEDEROS.keys()), key="cont_prod"
            )
            p_info = PRODUCTOS_PERECEDEROS[prod_key]
            metodo_num = st.selectbox(
                "Método de aproximación principal:",
                ["Runge-Kutta 4 (RK4)", "Euler Explícito", "SciPy (RK45 Adaptativo)"],
                key="cont_metodo",
            )
            mostrar_todos = st.checkbox(
                "Superponer los 3 métodos numéricos en la gráfica",
                value=True,
                key="cont_overlay",
            )
        with c2:
            usar_stock_actual = False
            if df_inventario is not None and prod_key in df_inventario["Producto"].values:
                usar_stock_actual = st.checkbox(
                    "Usar Stock Actual del Dashboard como S(0)",
                    value=False,
                    key="cont_use_curr",
                )
            s0_default = (
                float(
                    df_inventario.loc[
                        df_inventario["Producto"] == prod_key, "Stock Actual"
                    ].iloc[0]
                )
                if usar_stock_actual
                else float(p_info["s0_default"])
            )
            s0 = st.number_input(
                f"Inventario Inicial S(0) ({prod_key}):",
                min_value=1.0,
                max_value=5000.0,
                value=max(1.0, s0_default),
                step=10.0,
                key=f"cont_s0_{prod_key}_{usar_stock_actual}",
            )
            lambda_0 = st.number_input(
                "Tasa base de degradación (λ₀):",
                min_value=0.0,
                max_value=0.1,
                value=float(p_info["lambda_0"]),
                step=0.001,
                format="%.3f",
                key=f"cont_lam_{prod_key}",
            )
        with c3:
            t_max = st.slider("Días de simulación (t_max):", 5, 60, 30, 5, key="cont_tmax")
            n_pasos = st.slider(
                "Pasos de discretización (N):",
                min_value=10,
                max_value=500,
                value=60,
                step=10,
                key="cont_npasos",
                help="Valores pequeños de N permiten visualizar el error de truncamiento de Euler vs. RK4.",
            )
            temp_amb = st.slider(
                "Temperatura ambiental del almacén (°C):",
                0.0,
                40.0,
                18.0,
                0.5,
                key="cont_temp",
            )

    comp = comparar_metodos_numericos(
        prod_key, float(s0), float(lambda_0), float(temp_amb), float(t_max), int(n_pasos)
    )
    clave_sel = {
        "Euler Explícito": "euler",
        "Runge-Kutta 4 (RK4)": "rk4",
        "SciPy (RK45 Adaptativo)": "scipy",
    }[metodo_num]
    s_final = float(comp[clave_sel][-1])
    merma = float(s0) - s_final

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Producto", f"{prod_key} ({'Perecedero' if p_info['perecedero'] else 'No perecedero'})")
    k2.metric("Temp. Óptima vs. Actual", f"{p_info['temp_optima']:.0f} °C → {temp_amb:.1f} °C")
    k3.metric("Stock Final Estimado", f"{s_final:,.1f} unid.")
    k4.metric(
        "Pérdida por Merma",
        f"{merma:,.1f} unid.",
        delta=f"-{(merma / s0) * 100:.1f}%" if s0 > 0 else "0.0%",
        delta_color="inverse",
    )

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(
            graficar_comparativa_metodos(
                comp, prod_key, metodo_num, int(n_pasos), mostrar_todos
            ),
            use_container_width=True,
        )
    with col_g2:
        curvas_temp = curvas_sensibilidad_temperatura(
            prod_key, float(s0), float(lambda_0), [4.0, 10.0, 18.0, 25.0, 32.0], float(t_max), int(n_pasos)
        )
        st.plotly_chart(
            graficar_sensibilidad_termica(curvas_temp, prod_key),
            use_container_width=True,
        )

    st.subheader("📐 Precisión Numérica y Error de Truncamiento")
    st.dataframe(comp["tabla_error"], use_container_width=True, hide_index=True)


# ==============================================================================
# 6. EJECUCIÓN INDEPENDIENTE (MODO STANDALONE)
# ==============================================================================
if __name__ == "__main__":
    import streamlit as st

    st.set_page_config(
        page_title="Módulo 3 — Modelo Continuo EDO",
        page_icon="🧪",
        layout="wide",
    )
    render_modulo_continuo(None)