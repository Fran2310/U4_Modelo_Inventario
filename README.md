# 🛒 Simulador Integral de Inventario para Supermercado

**Materia:** DCM-902 — Diseño y Control de Modelos

**Proyecto:** Simulador Dinámico e Interactivo de Gestión, Simulación y Optimización de Inventarios

**Entorno de Ejecución:** Python 3.10+ | Streamlit | Pandas | NumPy | SciPy | Plotly

## 📖 Descripción General del Proyecto

Este proyecto implementa un **Simulador Interactivo de Inventario** para el canal supermercadista que unifica cuatro etapas de modelado matemático y computacional en una sola aplicación web (`main.py`). Permite gestionar existencias en tiempo real, proyectar la demanda estocástica bajo distintas políticas de reposición, resolver ecuaciones diferenciales ordinarias (EDO) de degradación térmica y ejecutar experimentos de optimización, validación Monte Carlo y análisis de sensibilidad con visualizaciones interactivas integradas.

## 🧱 Arquitectura Integral del Sistema (4 Módulos)

Los 4 módulos están implementados e integrados dentro de `main.py` mediante pestañas (`st.tabs`), manteniendo la capacidad de ejecutarse también de forma independiente para pruebas unitarias:

```
U4_Modelo_Inventario/
│
├── main.py                  # [Módulo 1 + App Integrada] Core CRUD, Dashboard y 4 Pestañas Interactivas
├── simulacion_discreta.py   # [Módulo 2] Simulación discreta día a día, políticas (s, Q) vs (R, S) y merma híbrida
├── modelo_continuo.py       # [Módulo 3] Modelado continuo de degradación de perecederos (EDO: Euler, RK4, SciPy)
├── control_optimo.py        # [Módulo 4] Modelo EOQ, optimización restringida, heatmaps, Monte Carlo y sensibilidad
├── requirements.txt         # Dependencias completas del proyecto
└── README.md                # Documentación técnica, resultados experimentales y conclusiones

```

## 🧩 Detalle por Módulos y Visualizaciones Integradas

### 🟢 Módulo 1: Core de Inventario, Costos Estáticos y Dashboard (`main.py`)
#### Encargado: Francisco Ramos
* **Gestión de Estado Centralizada:** Persistencia del catálogo en `st.session_state["inventario_df"]` para las 4 categorías base (`Carne`, `Lácteos`, `Granos`, `Higiene`), sincronizado con todas las pestañas de simulación.

* **Operaciones CRUD:** Entradas y salidas manuales desde la barra lateral con validación estricta de no-negatividad y reinicio rápido del estado base.

* **Modelo Estático de Costos (Lucro Cesante):** 

  $$
  \text{Costo Total} = \text{Costo de Compra} + \text{Costo de Almacenamiento} + \text{Lucro Cesante}
  $$

   donde el Lucro Cesante se activa para productos agotados ($\text{Stock}=0$) como $\sum (\text{Margen Unitario} \times \text{Stock Mínimo})$.

* **Visualizaciones Integradas (Pestaña 1):** Tarjetas KPI, alertas automáticas de stock bajo/agotado, gráfico de barras de **Stock Actual vs. Stock Mínimo** (con código de color por estado), gráfico circular de **Distribución del Valor Comercial** y tabla consolidada con fila de **TOTALES**.

### 🟢 Módulo 2: Simulación Discreta y Políticas de Reposición (`simulacion_discreta.py`)
#### Encargado: Kathryn Aguilar

* **Motor Secuencial de Intervalos:** Simula día a día la llegada de pedidos en tránsito (respetando el *lead time*), demanda normal estocástica $N(\mu, \sigma)$, ventas, faltantes, ciclo térmico $T(t) = T_{\text{base}} + A \cdot \sin(2\pi t / 30)$, merma híbrida cuando $T(t) > T_{\text{umbral}}$ y reposición basada en **posición de inventario** ($\text{stock físico} + \text{en tránsito}$).

* **Políticas Evaluadas:** Revisión continua $(s, Q)$ y revisión periódica $(R, S)$.

* **Visualizaciones Integradas (Pestaña 2):** Evolución comparativa del stock diario con líneas de quiebre y stock mínimo, gráfico combinado de **Temperatura Dinámica y Merma Diaria**, gráfico de barras de **Desglose Comparativo de Costos** (Compra, Almacenamiento, Lucro Cesante y Merma) y tabla de detalle diario.

### 🟢 Módulo 3: Modelos Continuos y Dinámica de Perecederos (`modelo_continuo.py`)
#### Encargado: Miguel Bracho

* **Formulación EDO:** Modela la degradación continua dependiente de la temperatura ambiental:
  

  $$
  \frac{dS}{dt} = -\lambda_0 \cdot e^{\alpha \cdot \max(0,\, T_{\text{amb}} - T_{\text{ópt}})} \cdot S(t)
  $$

* **Métodos Numéricos:** Implementación comparativa de **Euler Explícito**, **Runge-Kutta de 4to Orden (RK4)** y **SciPy RK45 adaptativo**, contrastados frente a la solución analítica exacta para cuantificar el error de truncamiento (Error Máximo y MAE).

* **Visualizaciones Integradas (Pestaña 3):** Superposición interactiva de los tres integradores numéricos, curvas de **Sensibilidad Térmica** ($4\,^\circ\text{C}$ a $32\,^\circ\text{C}$) y tabla de precisión numérica.

### 🟢 Módulo 4: Experimentación, Control Óptimo y Análisis de Sensibilidad (`control_optimo.py`)
#### Encargado: Jesus Ramirez

* **Modelo Analítico EOQ y Stock de Seguridad:** Calcula el lote económico $Q^* = \sqrt{\frac{2DK}{H}}$, el stock de seguridad $SS = z \cdot \sigma \cdot \sqrt{L}$ y el punto de reorden $ROP = \mu L + SS$.

* **Optimización por Barrido Restringido (Grid Search):** Evalúa mallas de $(s, Q)$ y $(R, S)$ imponiendo una restricción configurable de **Nivel de Servicio Mínimo** (por defecto $\ge 95\%$) para evitar soluciones degeneradas que minimizan compras a costa de desabastecer el supermercado.

* **Validación Monte Carlo y Sensibilidad:** Ejecuta $N$ réplicas estocásticas independientes para medir media y desviación de costos, y analiza la respuesta del sistema ante variaciones de *Lead Time*, Temperatura Base y Volatilidad de Demanda ($\sigma$).

* **Visualizaciones Integradas (Pestaña 4):**

  * Curva de compensación (**Trade-Off EOQ**) entre costo de ordenar y almacenar.

  * **Mapas de calor (Heatmaps)** de costo total para las mallas $(s, Q)$ y $(R, S)$ con marcador del óptimo factible.

  * Histogramas superpuestos de **distribución de costos Monte Carlo**.

  * Tres curvas de **análisis de sensibilidad** (*Lead Time*, Temperatura, Volatilidad).

  * **Comparativa global** de políticas óptimas para los 4 productos del supermercado.

## 📊 Resultados Experimentales

Los siguientes resultados fueron obtenidos ejecutando el motor integrado sobre el catálogo base con un horizonte de **30 días**, *lead time* $L = 3$ días, costo fijo por orden $K = \$25$, ciclo térmico $T_{\text{base}} = 20\,^\circ\text{C}$, $A = 8\,^\circ\text{C}$, umbral $26\,^\circ\text{C}$, merma de $3\%$ y restricción de nivel de servicio $\ge 95\%$:

### 1. Comparativa Global de Optimización por Producto

| Producto | Demanda ($\mu \pm \sigma$) | EOQ ($Q^*$) | ROP Analítico | Óptimo $(s, Q)$ | Costo $(s, Q)$ | Servicio $(s, Q)$ | Óptimo $(R, S)$ | Costo $(R, S)$ | Servicio $(R, S)$ | Mejor Política | Ahorro | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| **Carne** | 12 ± 3 | 30 | 45 | s=40, Q=30 | \$3,613.40 | 100.0% | R=3, S=80 | \$3,872.35 | 96.7% | **(s, Q)** | \$258.95 | 
| **Lácteos** | 22 ± 5 | 61 | 80 | s=60, Q=30 | \$2,026.80 | 96.2% | R=1, S=80 | \$2,077.20 | 100.0% | **(s, Q)** | \$50.40 | 
| **Granos** | 35 ± 7 | 148 | 125 | s=100, Q=65 | \$1,309.34 | 98.2% | R=1, S=120 | \$1,248.56 | 100.0% | **(R, S)** | \$60.78 | 
| **Higiene** | 18 ± 4 | 77 | 65 | s=60, Q=30 | \$1,870.25 | 100.0% | R=1, S=80 | \$1,925.05 | 100.0% | **(s, Q)** | \$54.80 | 

### 2. Robustez Estadística Monte Carlo (50 Réplicas — Carne)

| Política Evaluada | Costo Total Medio (\$) | Desviación Estándar (\$) | Nivel de Servicio Promedio (%) | 
| ----- | ----- | ----- | ----- | 
| $(s, Q)$ **Óptima** (`s=40, Q=30`) | **\$3,458.03** | ±\$132.92 | **99.80%** | 
| $(R, S)$ **Óptima** (`R=3, S=80`) | \$3,840.12 | ±\$102.73 | 96.16% | 

### 3. Precisión Numérica y Sensibilidad Térmica del Modelo Continuo (EDO, 30 días)

Comparativa de error frente a la solución analítica exacta para `Carne` a $18\,^\circ\text{C}$ con discretización gruesa ($N = 30$ pasos):

| Método Numérico | Stock Final (unid) | Merma Total (unid) | Error Máx vs. Exacta | MAE vs. Exacta | 
| ----- | ----- | ----- | ----- | ----- | 
| **Euler Explícito** | 1.523 | 798.477 | 31.18984 | 13.53069 | 
| **Runge-Kutta 4 (RK4)** | 2.860 | 797.140 | 0.00411 | 0.00187 | 
| **SciPy (RK45 Adaptativo)** | 2.860 | 797.140 | 0.00000 | 0.00000 | 

Impacto de la temperatura ambiental en la merma acumulada a 30 días (sin reposición, RK4):

| Producto | $4\,^\circ\text{C}$ | $12\,^\circ\text{C}$ | $18\,^\circ\text{C}$ | $25\,^\circ\text{C}$ | 
| ----- | ----- | ----- | ----- | ----- | 
| **Carne** ($S_0 = 800$) | 65.0% merma (280.0 unid) | 93.6% merma (51.5 unid) | 99.6% merma (2.9 unid) | 100.0% merma (0.0 unid) | 
| **Lácteos** ($S_0 = 1200$) | 45.1% merma (658.6 unid) | 64.3% merma (428.6 unid) | 82.9% merma (205.1 unid) | 96.4% merma (43.5 unid) | 

## 🧠 Conclusiones

1. **Superioridad de la revisión continua** $(s, Q)$ **en productos perecederos y de alto costo de almacenamiento:** Para `Carne`, `Lácteos` e `Higiene`, la política $(s, Q)$ superó a la revisión periódica $(R, S)$ manteniendo niveles de servicio superiores al 96% y logrando un ahorro de hasta **\$258.95** en `Carne` (y **\$382.09** en promedio a lo largo de 50 réplicas Monte Carlo, con 99.80% de servicio). En cambio, para `Granos` (alta rotación y bajo costo de almacenamiento de \$0.08/unidad), la revisión periódica $(R, S)$ con ciclos cortos resultó **\$60.78** más económica.

2. **Necesidad crítica de restricciones de nivel de servicio en la optimización:** Al incluir el costo de compra en la función objetivo sin ingresos por ventas, una optimización sin restricciones tiende a soluciones degeneradas (reducir pedidos y tolerar roturas masivas porque el costo de compra supera al margen unitario). Incorporar la restricción de **nivel de servicio** $\ge 95\%$ permitió alinear los parámetros simulados (`s=40, Q=30` en Carne) con los valores teóricos del modelo **EOQ/ROP** ($Q^*=30$, $ROP=45$).

3. **Impacto exponencial de la cadena de frío en el inventario:** Tanto el modelo híbrido discreto como la EDO continua demuestran que superar la temperatura óptima dispara las pérdidas: en el modelo discreto de `Carne`, elevar la temperatura base de $18\,^\circ\text{C}$ a $30\,^\circ\text{C}$ incrementó el costo en casi 10% bajo $(s, Q)$ y elevó la merma de 0 a 12 unidades (16 unidades en $(R, S)$ por mantener picos mayores de stock). En el modelo continuo, perder la refrigeración ($4\,^\circ\text{C} \to 18\,^\circ\text{C}$) eleva la degradación de `Carne` del 65.0% al 99.6% en 30 días.

4. **Confiabilidad de los métodos numéricos de orden superior:** Con discretizaciones bajas ($N=30$), el método de Euler Explícito introduce errores máximos superiores a **31 unidades**, mientras que **Runge-Kutta 4 (RK4)** reduce el error a **0.0041 unidades** (más de 7,500 veces más preciso) con el mismo costo computacional de pasos, igualando prácticamente la solución adaptativa de SciPy RK45.

5. **Valor de la integración visual para la toma de decisiones:** Consolidar el estado CRUD, las trayectorias estocásticas, las curvas de degradación EDO, los mapas de calor y las pruebas de sensibilidad en una única interfaz interactiva permite diagnosticar de inmediato el compromiso (*trade-off*) entre costo de almacenamiento, riesgo de quiebre y merma térmica.

## 🔌 Contratos de Integración

* **Estado global:** `st.session_state["inventario_df"]` compartido por los 4 módulos.

* **Funciones puras reutilizables:**

  * `main.calcular_costos_estaticos(df)`

  * `simulacion_discreta.simular(...)` y `simulacion_discreta.costos_simulacion(...)`

  * `modelo_continuo.resolver_modelo_continuo(...)` y `modelo_continuo.comparar_metodos_numericos(...)`

  * `control_optimo.calcular_eoq(...)`, `control_optimo.barrido_parametros(...)` y `control_optimo.simulacion_monte_carlo(...)`

## 🚀 Instalación y Puesta en Marcha

### Prerrequisitos

Python 3.10 o superior y `pip`.

### 1. Instalar las dependencias

```
pip install -r requirements.txt

```

### 2. Ejecutar la aplicación integrada

```
streamlit run main.py

```

La aplicación abrirá en `http://localhost:8501` con las 4 pestañas integradas. Cada módulo también puede ejecutarse de manera individual (`streamlit run simulacion_discreta.py`, `streamlit run modelo_continuo.py` o `streamlit run control_optimo.py`).
