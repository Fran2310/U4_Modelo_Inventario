# 🛒 Simulador de Inventario para Supermercado
**Materia:** DCM-902 — Diseño y Control de Modelos  
**Proyecto:** Simulador Dinámico e Interactivo de Gestión de Inventarios  
**Entorno de Ejecución:** Python 3.10+ | Streamlit | Pandas  

---

## 📖 Descripción General del Proyecto

Este proyecto consiste en el diseño, implementación y evaluación de un **Simulador Interactivo de Inventario** enfocado en el canal supermercadista. Su objetivo es modelar el comportamiento del inventario para categorías de productos representativas mediante un enfoque gradual que abarca desde la administración básica de existencias hasta la simulación estocástica y la optimización de políticas de reorden.

La aplicación permite analizar el impacto económico de los niveles de existencias, evaluar la función de costo total operativo y prevenir roturas de stock mediante indicadores analíticos en tiempo real.

---

## 🧱 Arquitectura Integral del Sistema (4 Módulos)

El proyecto se encuentra modularizado en 4 etapas analíticas e ingenieriles diseñadas para completarse de forma colaborativa:

```
U4_Modelo_Inventario/
│
├── main.py                  # [Módulo 1] Core de Inventario, UI Dashboard y Costos Estáticos
├── simulacion_discreta.py   # [Módulo 2] Simulación de demanda por eventos estocásticos (Monte Carlo)
├── modelo_continuo.py       # [Módulo 3] Modelado continuo de mermas y degradación (EDO)
├── control_optimo.py        # [Módulo 4] Algoritmos de control y políticas de reorden óptimo (s, S / EOQ)
├── requirements.txt         # Dependencias del proyecto
└── README.md                # Documentación técnica y académica
```

---

### Detalle por Módulos y Estado de Desarrollo

### 🟢 Módulo 1: Core de Inventario y Modelo Estático (Implementado)
* **Archivo:** `main.py`
* **Responsabilidades:**
  - **Gestión de Estado Centralizada:** Persistencia del inventario durante la sesión interactiva con `st.session_state`.
  - **Catálogo Base de Productos:** Monitoreo de 4 categorías clave (`Carne`, `Lácteos`, `Granos`, `Higiene`) con atributos económicos (`Precio Venta`, `Costo Compra`, `Costo Almacenamiento`, `Stock Actual`, `Stock Mínimo`).
  - **Operaciones CRUD:** Entradas (abastecimiento) y salidas (despacho/ventas) manuales desde la barra lateral con control estricto de no-negatividad.
  - **Modelo Estático de Costos:** Evaluación instantánea de los costos del sistema:
    $$\text{Costo Total} = \text{Costo de Compra} + \text{Costo de Almacenamiento} + \text{Costo de Faltantes}$$
    - **Costo de Compra:** $\sum (\text{Costo Compra} \times \text{Stock Actual})$
    - **Costo de Almacenamiento:** $\sum (\text{Costo Almacenamiento} \times \text{Stock Actual})$
    - **Penalización por Faltantes:** Multa económica fija ($\$150.00$) por cada producto con existencia en $0$.
  - **Dashboard de Monitoreo:** Métricas ejecutivas (KPIs), panel superior de alertas tempranas y tabla interactiva a ancho completo.

---

### ⏳ Módulo 2: Simulación de Eventos Discretos y Demanda Estocástica (Próximo)
* **Archivo objetivo:** `simulacion_discreta.py`
* **Alcance:**
  - Generación de demanda diaria de clientes utilizando distribuciones probabilísticas (ej. **Poisson** para afluencia y **Normal** truncada para volúmenes de compra).
  - Simulación de horizonte temporal discreto ($T = 30$ o $60$ días) mediante pasos de tiempo $\Delta t = 1 \text{ día}$.
  - Registro de series temporales de existencias, ventas perdidas por agotamiento y costos acumulados día a día.

---

### ⏳ Módulo 3: Modelos Continuos y Dinámica de Perecederos (Próximo)
* **Archivo objetivo:** `modelo_continuo.py`
* **Alcance:**
  - Formulación de **Ecuaciones Diferenciales Ordinarias (EDO)** para modelar la tasa de merma o degradación física de productos perecederos (particularmente `Carne` y `Lácteos`):
    $$\frac{dQ(t)}{dt} = - \lambda(T_{amb}) \cdot Q(t) - D(t)$$
    donde $\lambda(T_{amb})$ representa el factor de merma según condiciones térmicas y $D(t)$ la tasa continua de salida.
  - Integración numérica utilizando esquemas explícitos (Runge-Kutta / Euler) o la librería `scipy.integrate.solve_ivp`.

---

### ⏳ Módulo 4: Políticas de Control y Optimización de Inventarios (Próximo)
* **Archivo objetivo:** `control_optimo.py`
* **Alcance:**
  - Implementación de políticas de inventario estocásticas tipo $(s, S)$ o $(r, Q)$ con tiempo de entrega (Lead Time $L$).
  - Determinación del lote económico de compra (**EOQ**) y punto de reorden óptimo equilibrando el costo de ordenar ($K$), costo de almacenamiento ($h$) y penalización por rotura ($p$).
  - Curvas de compensación (Trade-off) y análisis de sensibilidad de parámetros.

---

## 🔌 Guía de Integración y Contratos de Datos (Para el Equipo)

Para facilitar la integración modular por parte de los compañeros de equipo, el Core expone los siguientes puntos de enlace:

### 1. Estado Global del Inventario (`st.session_state`)
El DataFrame está disponible globalmente bajo la clave:
```python
import streamlit as st

df_actual = st.session_state["inventario_df"]
```

**Estructura de Columnas:**
| Columna | Tipo de Dato | Descripción |
| :--- | :---: | :--- |
| `Producto` | `str` | Nombre o categoría del artículo |
| `Precio Venta ($)` | `float` | Precio unitario al público |
| `Costo Compra ($)` | `float` | Costo unitario de adquisición |
| `Costo Almacenamiento ($/unidad)` | `float` | Tarifa de mantenimiento/refrigeración |
| `Stock Actual` | `int` | Existencia física disponible |
| `Stock Mínimo` | `int` | Punto de seguridad o reorden base |

### 2. Calculadora de Costos (`calcular_costos_estaticos`)
La función de costos es pura (no tiene efectos secundarios), lo que permite utilizarla tanto en la interfaz como en algoritmos de optimización:
```python
from main import calcular_costos_estaticos

costo_compra, costo_almacen, costo_faltantes = calcular_costos_estaticos(df)
```

### 3. Inyección de Módulos Futuros en la Interfaz
En las próximas entregas, los módulos de simulación pueden conectarse en la barra lateral o en pestañas (`st.tabs`):
```python
# Ejemplo de integración futura para Módulo 2 y Módulo 3:
tab_dashboard, tab_simulacion, tab_control = st.tabs([
    "📊 Monitoreo Actual",
    "🎲 Simulación Estocástica",
    "⚙️ Políticas de Control"
])
```

---

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos
Tener instalado Python 3.10 o superior y el gestor de paquetes `pip`.

### 1. Clonar o abrir el directorio del proyecto
```bash
cd "c:\Users\User\Documents\UMC\UMC files\2026-01\3. DCM-902 Diseño de Control y Modelos\U4_Modelo_Inventario"
```

### 2. Instalar las dependencias requeridas
```bash
pip install -r requirements.txt
```

### 3. Ejecutar la aplicación
```bash
streamlit run main.py
```
La aplicación se desplegará localmente en `http://localhost:8501`.

---

## 👥 Colaboración y Buenas Prácticas
- **Estilo de Código:** Cumplimiento de **PEP 8** y tipado estático con `typing`.
- **Inmutabilidad en cálculos:** Mantener las funciones de modelado como funciones puras para facilitar pruebas unitarias.
- **Validaciones:** Comprobar siempre que las salidas de stock no generen existencias negativas.
