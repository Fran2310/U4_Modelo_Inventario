import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
import pandas as pd


# ==========================================
# 1. DICCIONARIO OFICIAL DE LOS 4 PRODUCTOS
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
# 2. FUNCIÓN DE TASA DE CAMBIO (EDO Base)
# ==========================================
def tasa_degradacion(t, S, lambda_base, temp_amb, props):
    """Calcula la derivada dS/dt según la temperatura y sensibilidad del producto."""
    if not props["perecedero"] or S <= 0:
        return 0.0
    delta_temp = max(0.0, temp_amb - props["temp_optima"])
    factor_temp = np.exp(props["sensibilidad_temp"] * delta_temp)
    return - (lambda_base * factor_temp) * S

# ==========================================
# 3. MÉTODOS NUMÉRICOS DE APROXIMACIÓN
# ==========================================
def resolver_euler(s0, lambda_base, temp_amb, props, t_max=30, n_pasos=300):
    """Método de Euler Explícito (Primer orden) con paso configurable."""
    t = np.linspace(0, t_max, n_pasos)
    dt = t[1] - t[0]
    y = np.zeros(n_pasos)
    y[0] = s0
    for i in range(n_pasos - 1):
        dy = tasa_degradacion(t[i], y[i], lambda_base, temp_amb, props)
        y[i+1] = y[i] + dt * dy
        if y[i+1] < 0: y[i+1] = 0.0
    return t, y

def resolver_rk4(s0, lambda_base, temp_amb, props, t_max=30, n_pasos=300):
    """Método clásico de Runge-Kutta de 4to Orden (RK4) con paso configurable."""
    t = np.linspace(0, t_max, n_pasos)
    dt = t[1] - t[0]
    y = np.zeros(n_pasos)
    y[0] = s0
    for i in range(n_pasos - 1):
        ti, yi = t[i], y[i]
        k1 = tasa_degradacion(ti, yi, lambda_base, temp_amb, props)
        k2 = tasa_degradacion(ti + 0.5*dt, yi + 0.5*dt*k1, lambda_base, temp_amb, props)
        k3 = tasa_degradacion(ti + 0.5*dt, yi + 0.5*dt*k2, lambda_base, temp_amb, props)
        k4 = tasa_degradacion(ti + dt, yi + dt*k3, lambda_base, temp_amb, props)
        
        y[i+1] = yi + (dt / 6.0) * (k1 + 2.0*k2 + 2.0*k3 + k4)
        if y[i+1] < 0: y[i+1] = 0.0
    return t, y

def resolver_scipy(s0, lambda_base, temp_amb, props, t_max=30, n_puntos=300):
    """Método Adaptativo Dormand-Prince (Runge-Kutta 4(5)) vía SciPy."""
    t_eval = np.linspace(0, t_max, n_puntos)
    if not props["perecedero"]:
        return t_eval, np.full_like(t_eval, s0)
        
    def sistema(t, y):
        return [tasa_degradacion(t, y[0], lambda_base, temp_amb, props)]
        
    sol = solve_ivp(fun=sistema, t_span=(0, t_max), y0=[s0], t_eval=t_eval)
    return sol.t, sol.y[0]

# Función envoltorio principal (para importar limpiamente)
def resolver_modelo_continuo(nombre_producto, s0, lambda_base, temp_amb, t_max=30, metodo="Runge-Kutta 4 (RK4)", n_pasos=300):
    props = PRODUCTOS_PERECEDEROS.get(nombre_producto, PRODUCTOS_PERECEDEROS["Carne"])
    
    if metodo == "Euler Explícito":
        return resolver_euler(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    elif metodo == "Runge-Kutta 4 (RK4)":
        return resolver_rk4(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    else:
        return resolver_scipy(s0, lambda_base, temp_amb, props, t_max, n_pasos)


def comparar_metodos_numericos(nombre_producto, s0, lambda_base, temp_amb, t_max=30.0, n_pasos=150):
    props = PRODUCTOS_PERECEDEROS.get(nombre_producto, PRODUCTOS_PERECEDEROS["Carne"])
    t_eu, y_eu = resolver_euler(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    t_rk, y_rk = resolver_rk4(s0, lambda_base, temp_amb, props, t_max, n_pasos)
    t_sp, y_sp = resolver_scipy(s0, lambda_base, temp_amb, props, t_max, n_pasos)

    if props["perecedero"]:
        delta_temp = max(0.0, temp_amb - float(props["temp_optima"]))
        lambda_eff = lambda_base * float(np.exp(float(props["sensibilidad_temp"]) * delta_temp))
        y_exact = s0 * np.exp(-lambda_eff * t_eu)
    else:
        y_exact = np.full_like(t_eu, s0, dtype=float)

    tabla_error = pd.DataFrame([
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
    ])
    return {"t": t_eu, "euler": y_eu, "rk4": y_rk, "scipy": y_sp, "exacta": y_exact, "tabla_error": tabla_error}


def curvas_sensibilidad_temperatura(nombre_producto, s0, lambda_base, temperaturas=None, t_max=30.0, n_pasos=150):
    if temperaturas is None:
        temperaturas = [4.0, 10.0, 18.0, 25.0, 32.0]
    return {
        temp: resolver_modelo_continuo(nombre_producto, s0, lambda_base, temp, t_max, "Runge-Kutta 4 (RK4)", n_pasos)
        for temp in temperaturas
    }


def render_modulo_continuo(df_inventario=None):
    st.header("🧪 Modelo Continuo y Dinámica de Perecederos (EDO)")
    with st.expander("⚙️ Configurar Parámetros del Modelo Continuo", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            prod_key = st.selectbox("Producto:", list(PRODUCTOS_PERECEDEROS.keys()), key="cont_prod")
            p_info = PRODUCTOS_PERECEDEROS[prod_key]
            metodo_num = st.selectbox(
                "Método principal:",
                ["Runge-Kutta 4 (RK4)", "Euler Explícito", "SciPy (RK45 Adaptativo)"],
                key="cont_metodo",
            )
            mostrar_todos = st.checkbox("Superponer los 3 métodos", value=True, key="cont_overlay")
        with c2:
            usar_actual = (
                df_inventario is not None
                and prod_key in df_inventario["Producto"].values
                and st.checkbox("Usar Stock Actual como S(0)", value=False, key="cont_use_curr")
            )
            s0_def = (
                float(df_inventario.loc[df_inventario["Producto"] == prod_key, "Stock Actual"].iloc[0])
                if usar_actual else float(p_info["s0_default"])
            )
            s0 = st.number_input(f"Inventario Inicial S(0) ({prod_key}):", 1.0, 5000.0, max(1.0, s0_def), 10.0, key=f"cont_s0_{prod_key}_{usar_actual}")
            lambda_0 = st.number_input("Tasa base (λ₀):", 0.0, 0.1, float(p_info["lambda_0"]), 0.001, format="%.3f", key=f"cont_lam_{prod_key}")
        with c3:
            t_max = st.slider("Días (t_max):", 5, 60, 30, 5, key="cont_tmax")
            n_pasos = st.slider("Pasos (N):", 10, 500, 60, 10, key="cont_npasos")
            temp_amb = st.slider("Temperatura (°C):", 0.0, 40.0, 18.0, 0.5, key="cont_temp")

    comp = comparar_metodos_numericos(prod_key, float(s0), float(lambda_0), float(temp_amb), float(t_max), int(n_pasos))
    clave = {"Euler Explícito": "euler", "Runge-Kutta 4 (RK4)": "rk4", "SciPy (RK45 Adaptativo)": "scipy"}[metodo_num]
    s_final = float(comp[clave][-1])
    merma = float(s0) - s_final

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Producto", prod_key)
    k2.metric("Temp. Óptima → Actual", f"{p_info['temp_optima']:.0f} °C → {temp_amb:.1f} °C")
    k3.metric("Stock Final Estimado", f"{s_final:,.1f} unid.")
    k4.metric("Pérdida por Merma", f"{merma:,.1f} unid.", delta=f"-{(merma/s0)*100:.1f}%" if s0 > 0 else "0.0%", delta_color="inverse")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig = go.Figure()
        if mostrar_todos:
            fig.add_trace(go.Scatter(x=comp["t"], y=comp["euler"], mode="lines", name="Euler Explícito", line=dict(color="#ef553b", dash="dot")))
            fig.add_trace(go.Scatter(x=comp["t"], y=comp["rk4"], mode="lines", name="Runge-Kutta 4 (RK4)", line=dict(color="#00cc96", width=3)))
            fig.add_trace(go.Scatter(x=comp["t"], y=comp["scipy"], mode="lines", name="SciPy RK45", line=dict(color="#636efa", dash="dash")))
        else:
            fig.add_trace(go.Scatter(x=comp["t"], y=comp[clave], mode="lines", name=metodo_num, line=dict(color="#ffa15a", width=3)))
        fig.update_layout(title=f"Comparativa de Métodos — {prod_key} (N={n_pasos})", xaxis_title="Días", yaxis_title="Unidades", hovermode="x unified", height=380)
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        curvas = curvas_sensibilidad_temperatura(prod_key, float(s0), float(lambda_0), [4.0, 10.0, 18.0, 25.0, 32.0], float(t_max), int(n_pasos))
        fig_t = go.Figure()
        for temp, (tv, sv) in curvas.items():
            fig_t.add_trace(go.Scatter(x=tv, y=sv, mode="lines", name=f"{temp:.0f} °C"))
        fig_t.update_layout(title=f"🌡️ Sensibilidad Térmica — {prod_key}", xaxis_title="Días", yaxis_title="Stock remanente", hovermode="x unified", height=380)
        st.plotly_chart(fig_t, use_container_width=True)

    st.subheader("📐 Precisión Numérica y Error de Truncamiento")
    st.dataframe(comp["tabla_error"], use_container_width=True, hide_index=True)


# ==========================================
# 4. INTERFAZ VISUAL EN STREAMLIT
# ==========================================
if __name__ == "__main__":
    try:
        st.set_page_config(page_title="Módulo Continuo - Métodos Numéricos", layout="wide")
    except Exception:
        pass

    st.title("📦 Módulo 3: EDOs y Simulación Continua con Métodos Numéricos")
    st.markdown("Comparativa de algoritmos de aproximación y control de discretización para perecederos.")

    st.sidebar.header("⚙️ Configuración del Modelo")
    prod_key = st.sidebar.selectbox("Seleccione el Producto", list(PRODUCTOS_PERECEDEROS.keys()))
    
    metodo_num = st.sidebar.selectbox(
        "Método de Aproximación Numérica",
        ["Runge-Kutta 4 (RK4)", "Euler Explícito", "SciPy (RK45 Adaptativo)"]
    )
    
    p_info = PRODUCTOS_PERECEDEROS[prod_key]
    
    t_max = st.sidebar.slider("Días de simulación ($t_{max}$)", 5, 60, 30, 5)
    
    # Control dinámico de pasos (solo se activa de forma útil para Euler y RK4 manual)
    if metodo_num != "SciPy (RK45 Adaptativo)":
        n_pasos = st.sidebar.slider("Número de Pasos / Discretización ($N$)", min_value=10, max_value=1000, value=150, step=10,
                                     help="Menos pasos = mayor error de truncamiento. Más pasos = mayor precisión.")
    else:
        n_pasos = 300
        st.sidebar.info("ℹ️ SciPy gestiona el paso de forma adaptativa automática.")

    s0 = st.sidebar.number_input(f"Inventario Inicial S(0) para {prod_key}", 10.0, 5000.0, p_info["s0_default"], 50.0)
    lambda_0 = st.sidebar.number_input(r"Tasa base de degradación ($\lambda_0$)", 0.0, 0.1, p_info["lambda_0"], 0.001, format="%.3f")
    temp_amb = st.sidebar.slider("Temperatura ambiental del almacén (°C)", 0.0, 40.0, 18.0, 0.5)

    # Ejecutar cálculo pasando el número de pasos
    t_vals, s_vals = resolver_modelo_continuo(prod_key, s0, lambda_0, temp_amb, t_max, metodo_num, n_pasos)

    # Métricas en pantalla
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Producto", prod_key)
    col2.metric("Método", metodo_num.split()[0])
    col3.metric("Stock Final Estimado", f"{s_vals[-1]:,.1f} unds")
    merma = s0 - s_vals[-1]
    col4.metric("Pérdida por Merma", f"{merma:,.1f} unds", delta=f"-{(merma/s0)*100:.1f}%" if s0 > 0 else "0.0%", delta_color="inverse")

    st.markdown("---")

    # Gráfica Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_vals, y=s_vals, mode='lines+markers' if n_pasos < 40 else 'lines', 
        name=f'{prod_key} ({metodo_num})',
        line=dict(color='#00d4b6' if not p_info["perecedero"] else '#ffa15a', width=3)
    ))
    fig.update_layout(
        title=f"Evolución del Inventario - {metodo_num} (N = {n_pasos} pasos)",
        xaxis_title="Tiempo (Días)",
        yaxis_title="Unidades Físicas Disponibles",
        template="plotly_dark",
        hovermode="x unified"
    )
    st.plotly_chart(fig, width='stretch')

