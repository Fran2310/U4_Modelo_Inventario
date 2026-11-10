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
  - **Catálogo Base de Productos:** Monitoreo de 4 categorías clave (`Carne`, `Lácteos`, `Granos`, `Higiene`) con atributos económicos (`Precio Venta`, `Costo Compra`, `Margen Unitario`, `Costo Almacenamiento`, `Stock Actual`, `Stock Mínimo`).
  - **Operaciones CRUD:** Entradas (abastecimiento) y salidas (despacho/ventas) manuales desde la barra lateral con control estricto de no-negatividad.
  - **Modelo Estático de Costos (Lucro Cesante):** Evaluación instantánea de los costos del sistema:
    $$\text{Costo Total} = \text{Costo de Compra} + \text{Costo de Almacenamiento} + \text{Lucro Cesante}$$
    - **Costo de Compra:** $\sum (\text{Costo Compra} \times \text{Stock Actual})$
    - **Costo de Almacenamiento:** $\sum (\text{Costo Almacenamiento} \times \text{Stock Actual})$
    - **Lucro Cesante (Faltantes):** Penalización dinámica equivalente al margen de ganancia perdido por demanda insatisfecha estimada sobre el stock mínimo:
      $$\text{Lucro Cesante} = \sum_{\text{Stock}=0} (\text{Margen Unitario} \times \text{Stock Mínimo})$$
  - **Dashboard de Monitoreo:** Métricas ejecutivas (KPIs), panel superior de alertas tempranas y tabla interactiva a ancho completo con fila consolidada de **TOTALES** (Stock total y Valor comercial agregado).

---

### ⏳ Módulo 2: Simulación de Eventos Discretos y Demanda Estocástica (Próximo)
* **Archivo objetivo:** `simulacion_discreta.py`
* **Alcance:**
  📘 Explicación del Módulo 2 — Simulación Discreta y Políticas de Reposición
El Módulo 2 es el corazón analítico del sistema: toma el inventario que gestionas manualmente (Módulo 1) y lo proyecta 30 días en el futuro simulando cómo evolucionaría bajo demanda incierta y distintas reglas de reposición.

🎯 ¿Qué hace exactamente?
Simula día a día lo que ocurre en el almacén durante 30 jornadas, respondiendo preguntas como:
- **¿Cuántas unidades tendré mañana si la demanda es alta?**
- **¿Cuándo debo hacer un pedido y cuánto?**
- **¿Qué pasa si la temperatura sube y daña la mercancía?**
- **¿Qué política de reposición me cuesta menos dinero?**

⚙️ Los 5 subprocesos que ocurren en cada día simulado
Dentro del bucle for dia in range(1, dias+1) de la función simular(), en cada iteración se ejecuta esta secuencia:

**#	Subproceso	Qué simula**

**- 1	Llegada de pedidos**:Si un pedido hecho días atrás ya cumplió su lead time, entra al stock físico.

**- 2	Demanda aleatoria**:Se genera la demanda del día con una distribución normal N(μ, σ) → representa clientes que llegan de forma impredecible.

**- 3	Ventas y faltantes**:Si hay stock suficiente se vende todo; si no, lo no satisfecho se registra como faltante (venta perdida).

**- 4	Temperatura + merma**:Se calcula T(t) = base + A·sin(2π·t/30) y, si supera el umbral, se descuenta un % del stock como merma (modelo híbrido).

**- 5	Decisión de pedido**:Se evalúa la política activa para decidir si se hace un pedido hoy y cuánto.

**🔄 Las dos políticas de reposición implementadas**
📦 Política (s, Q) — Revisión Continua
Regla: "Si la posición de inventario cae por debajo de s, pido Q unidades fijas."

Cómo se comporta: pedidos frecuentes y de tamaño constante. Mantiene el stock más "estable".

Ejemplo: si s=20 y Q=50, cada vez que el inventario toque 20, se piden 50.

📦 Política (R, S) — Revisión Periódica
Regla: "Cada R días reviso y pido lo necesario para llegar a S."

Cómo se comporta: pedidos agrupados (menos frecuentes) pero de tamaño variable. Reduce costos de compra pero puede generar más faltantes si R es grande.

Ejemplo: si R=5 y S=150, cada 5 días se pide lo que falte para tener 150 unidades.

- 🔑 Clave técnica: posición de inventario
Ambas políticas usan posicion = stock + pedidos_en_tránsito (no solo el stock físico). Esto evita pedidos duplicados mientras el pedido anterior aún está en camino por el lead time.

- 🌡️ Los dos modelos especiales que se combinan
**Modelo dinámico continuo — Temperatura**
text
T(t) = 20 + 8·sin(2π·t/30)
Simula un ciclo térmico (día caluroso → fresco → caluroso) sin saltos bruscos, como ocurre en un almacén real. Se grafica superpuesto con el stock para ver el efecto.

**Modelo híbrido — Merma por calor**
Cuando T(t) > umbral (26°C), el sistema pierde un porcentaje del stock disponible:

**text**
if T > umbral: merma = stock × tasa (ej. 3%)
Esto acopla la variable continua (temperatura) con el inventario discreto, cumpliendo el requisito del enunciado.

**💰 ¿Qué obtiene el usuario al final?**
Tabla diaria de 30 filas con: demanda, ventas, faltantes, temperatura, merma, pedido, stock final.

Gráfico comparativo de stock entre política (s,Q) y (R,S), con línea de stock mínimo y quiebre.

Gráfico de temperatura mostrando cuándo se activó la merma.

Tabla de costos desglosada por política:

Costo de Compra = Σ pedidos × costo unitario

Costo de Almacenamiento = stock promedio × costo diario × días

Lucro Cesante = Σ faltantes × margen unitario

Pérdida por Merma = Σ mermas × costo unitario

Recomendación automática: la política con menor costo total.

- **🔬 Submódulo de Optimización** Barre automáticamente combinaciones de (s, Q) y (R, S) (varias decenas) y ordena los resultados por costo total, identificando la configuración óptima para ese producto y contexto.

**📊 En una frase** El Módulo 2 convierte el inventario estático en una película de 30 días, donde la demanda, la temperatura y la política de pedidos interactúan para producir costos, faltantes y mermas medibles — permitiéndote decidir con evidencia qué política conviene al negocio.



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

**Estructura de Columnas en `st.session_state`:**
| Columna | Tipo de Dato | Descripción |
| :--- | :---: | :--- |
| `Producto` | `str` | Nombre o categoría del artículo |
| `Precio Venta ($)` | `float` | Precio unitario al público |
| `Costo Compra ($)` | `float` | Costo unitario de adquisición |
| `Margen Unitario ($)` | `float` | Margen de ganancia (`Precio Venta - Costo Compra`) |
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
