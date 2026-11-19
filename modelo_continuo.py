import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go

# ==========================================
#DICCIONARIO DE PRODUCTOS
# ==========================================
PRODUCTOS_PERECEDEROS = {
    "Carne": {
        "s0_default": 800.0,
        "lambda_0": 0.035,
        "sensibilidad_temp": 0.12,
        "temp_optima": 4.0,
        "perecedero": True
    },
    "Lácteos": {
        "s0_default": 1200.0,
        "lambda_0": 0.020,
        "sensibilidad_temp": 0.09,
        "temp_optima": 6.0,
        "perecedero": True
    },
    "Granos": {
        "s0_default": 2500.0,
        "lambda_0": 0.002,
        "sensibilidad_temp": 0.01,
        "temp_optima": 20.0,
        "perecedero": False
    },
    "Higiene": {
        "s0_default": 1500.0,
        "lambda_0": 0.0,
        "sensibilidad_temp": 0.0,
        "temp_optima": 25.0,
        "perecedero": False
    }
}

# ==========================================
# 2. FUNCIÓN DE CÁLCULO (Importable)
# ==========================================
def resolver_modelo_continuo(nombre_producto, s0, lambda_base, temp_amb, t_max=30):
    """
    Resuelve el sistema de EDOs para la degradación del inventario 
    en función de la temperatura ambiental y la cinética del producto.
    """
    props = PRODUCTOS_PERECEDEROS.get(nombre_producto, PRODUCTOS_PERECEDEROS["Carne"])
    
    if not props["perecedero"]:
        # Si no es perecedero (Higiene/Granos), el stock se mantiene constante o con decaimiento mínimo
        t_eval = np.linspace(0, t_max, 300)
        y_sol = np.full_like(t_eval, s0)
        return t_eval, y_sol

    def sistema_edos(t, y):
        S = y[0]
        # Factor de Arrhenius para productos perecederos
        delta_temp = max(0.0, temp_amb - props["temp_optima"])
        factor_temp = np.exp(props["sensibilidad_temp"] * delta_temp)
        tasa_efectiva = lambda_base * factor_temp
        dS_dt = -tasa_efectiva * S
        return [dS_dt]

    t_eval = np.linspace(0, t_max, 300)
    sol = solve_ivp(
        fun=sistema_edos,
        t_span=(0, t_max),
        y0=[s0],
        t_eval=t_eval
    )
    return sol.t, sol.y[0]


# ==========================================
# 3. INTERFAZ VISUAL (Solo si se ejecuta directo)
# ==========================================
if __name__ == "__main__" or "streamlit" in __name__:
    try:
        st.set_page_config(page_title="Módulo Continuo - Supermercado", layout="wide")
    except Exception:
        pass

    st.title("📦 Módulo 3: Dinámica Continua y EDOs de Inventario")
    st.markdown("Modelo oficial basado en los 4 productos estándar del supermercado.")

    st.sidebar.header("Parámetros de Simulación")
    prod_key = st.sidebar.selectbox("Seleccione el Producto", list(PRODUCTOS_PERECEDEROS.keys()))
    
    p_info = PRODUCTOS_PERECEDEROS[prod_key]
    
    t_max = st.sidebar.slider("Días de simulación ($t_{max}$)", 5, 60, 30, 5)
    s0 = st.sidebar.number_input(f"Inventario Inicial S(0) para {prod_key}", 10.0, 5000.0, p_info["s0_default"], 50.0)
    lambda_0 = st.sidebar.number_input(r"Tasa base de degradación ($\lambda_0$)", 0.0, 0.1, p_info["lambda_0"], 0.001, format="%.3f")
    temp_amb = st.sidebar.slider("Temperatura ambiental del almacén (°C)", 0.0, 40.0, 18.0, 0.5)

    # Ejecutar cálculo
    t_vals, s_vals = resolver_modelo_continuo(prod_key, s0, lambda_0, temp_amb, t_max)

    # Métricas
    col1, col2, col3 = st.columns(3)
    col1.metric("Producto", prod_key)
    col2.metric("Stock Final Estimado", f"{s_vals[-1]:,.1f} unds")
    merma = s0 - s_vals[-1]
    col3.metric("Pérdida por Merma", f"{merma:,.1f} unds", delta=f"-{(merma/s0)*100:.1f}%" if s0 > 0 else "0.0%", delta_color="inverse")

    st.markdown("---")

    # Gráfica Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_vals, y=s_vals, mode='lines', name=f'Inventario de {prod_key}',
        line=dict(color='#00d4b6' if not p_info["perecedero"] else '#ff4b4b', width=3)
    ))
    fig.update_layout(
        title=f"Curva de Evolución Temporal - {prod_key}",
        xaxis_title="Tiempo (Días)",
        yaxis_title="Unidades Físicas",
        template="plotly_dark",
        hovermode="x unified"
    )
    st.plotly_chart(fig, width='stretch')

