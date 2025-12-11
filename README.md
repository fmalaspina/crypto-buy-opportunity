# 🚀 Analista Cuantitativo - DCA con Valor Agregado

## Descripción

Este proyecto implementa un **analista cuantitativo profesional** diseñado específicamente para optimizar inversiones DCA (Dollar Cost Averaging) en criptomonedas, con tres herramientas principales:

1. **Analista Principal** - Análisis en tiempo real con identificación automática del mejor día
2. **Backtester Histórico** - Análisis de patrones temporales desde 2020
3. **Sistema de Explicación** - Guía detallada de métricas y rangos DCA

El sistema **identifica automáticamente el mejor día histórico** para DCA y se adapta dinámicamente, sin estar limitado a ningún día específico de la semana.

## Características Principales

### 📊 Indicadores Técnicos Implementados

1. **RSI (Relative Strength Index)** - Identifica condiciones de sobrecompra/sobreventa
2. **Bollinger Bands %B** - Mide la posición del precio dentro de las bandas
3. **Z-Score** - Estadística normalizada del precio vs media histórica
4. **Análisis de Volumen** - Detecta presión compradora/vendedora
5. **MACD Histogram** - Indicador de momentum y reversiones
6. **ROC (Rate of Change)** - Velocidad del cambio de precio

### 🗓️ Análisis Temporal Inteligente para DCA

- **🆕 IDENTIFICACIÓN AUTOMÁTICA DEL MEJOR DÍA**: Sistema dinámico que encuentra el día óptimo histórico
- **Ranking de Días**: Clasifica todos los días de la semana por rendimiento histórico
- **Análisis Adaptivo**: Se ajusta automáticamente sin depender de días específicos prefijados
- **Timing Óptimo**: Proporciona recomendaciones basadas en el día más favorable identificado
- **Flexibilidad Total**: Ejecuta el análisis cualquier día para obtener recomendaciones actualizadas

### 💰 Sistema de Inversión Inteligente

- **Inversión Base**: $250 USD (configurable)
- **Rango Dinámico**: 50% a 200% de la inversión base ($125 - $500)
- **Multiplicador Automático**: Basado en score cuantitativo combinado
- **Símbolo Configurable**: BTC por defecto, modificable por variable

## Instalación

```bash
pip install -r requirements.txt
```

## Archivos del Proyecto

### 1. `crypto_buy_opportunity.py` - Analista Principal
Análisis en tiempo real para decisiones de DCA optimizadas para lunes.

### 2. `dca_timing_backtest.py` - Backtester Histórico
Analiza patrones históricos desde 2020 para identificar mejores momentos de compra.

### 3. `demo_best_day.py` - Demo de Mejor Día
Demostración específica del análisis del mejor día de la semana para DCA.

### 4. `requirements.txt` - Dependencias
Lista de paquetes necesarios para el funcionamiento.

## Uso

### Análisis Principal (Tiempo Real)

```bash
# Análisis de BTC (por defecto)
python crypto_buy_opportunity.py

# Para otros símbolos, modificar en el código:
analyst = QuantitativeAnalyst(base_investment=250.0, symbol="ETHUSDT")
```

### Backtesting Histórico

```bash
# Análisis histórico completo de BTC desde 2020
python dca_timing_backtest.py

# Para otros símbolos, modificar en el código:
backtester = DCATimingBacktester("ETHUSDT")
```

### Uso Programático

```python
# Análisis Principal
from crypto_buy_opportunity import QuantitativeAnalyst

analyst = QuantitativeAnalyst(base_investment=300.0, symbol="BTCUSDT")
analyst.generate_report()

# Análisis específico del mejor día de la semana
timing_info = analyst.get_enhanced_timing_info()
print(f"Mejor día histórico: {timing_info['best_day']}")
print(f"Score: {timing_info['best_day_score']:.4f}")
print(f"Confianza: {timing_info['best_day_confidence']}")

# Backtesting
from dca_timing_backtest import DCATimingBacktester

backtester = DCATimingBacktester("BTCUSDT")
results = backtester.generate_backtest_report()
```

### Demo del Análisis de Mejor Día

```bash
# Ejecutar demo específico para análisis de días
python demo_best_day.py
```

## Interpretación de Resultados

### Score Cuantitativo (Analista Principal)
- **≥ 0.5**: 🟢 COMPRA FUERTE (hasta 2x inversión)
- **0.2 a 0.5**: 🔵 COMPRA MODERADA (1.2x a 1.5x inversión)
- **-0.2 a 0.2**: 🟡 NEUTRAL (inversión normal)
- **-0.5 a -0.2**: 🟠 PRECAUCIÓN (0.8x a 0.9x inversión)
- **< -0.5**: 🔴 EVITAR COMPRA (0.5x inversión mínima)

### Explicación Detallada de Métricas

El script principal incluye explicaciones automáticas de cada métrica:

#### RSI (Relative Strength Index)
- **< 30**: 🟢 OVERSOLD - Máxima oportunidad (+80-100%)
- **30-40**: 🔵 Levemente oversold - Buena oportunidad (+40-70%)
- **40-60**: 🟡 Zona neutral - DCA normal (±0%)
- **60-70**: 🟠 Levemente overbought - Reducir (-20%)
- **> 70**: 🔴 OVERBOUGHT - Evitar compra (-50%)

#### Bollinger %B
- **≤ 0**: 🟢 Precio debajo banda inferior (+100%)
- **0-0.2**: 🔵 Cerca banda inferior (+70%)
- **0.2-0.8**: 🟡 Rango medio (±0%)
- **0.8-1.0**: 🟠 Cerca banda superior (-30%)
- **> 1.0**: 🔴 Arriba banda superior (-50%)

#### Z-Score
- **≤ -2**: 🟢 Muy por debajo promedio (+100%)
- **-2 a -1**: 🔵 Por debajo promedio (+60%)
- **-1 a +1**: 🟡 Cerca del promedio (±0%)
- **+1 a +2**: 🟠 Por arriba promedio (-40%)
- **> +2**: 🔴 Muy por arriba promedio (-50%)

### Resultados de Backtesting

El backtester muestra:
- **Mejores meses del año** para DCA (análisis histórico)
- **Mejores semanas del año** con mayor probabilidad de éxito
- **Análisis por rangos de indicadores** técnicos
- **Comparación de estrategias** DCA vs estrategias condicionales

#### Ejemplo de Resultados Históricos (2020-2025):
- **Mejores meses**: Mayo (+9.2%), Abril (+5.0%), Agosto (+3.8%)
- **Mejores semanas**: Semana 17-18 del año (~Abril-Mayo)
- **Estrategia óptima**: DCA regular semanal mostró mejor return total

## Timeframes Analizados
1. **1d (Diario)** - Peso: 50%
2. **4h (4 horas)** - Peso: 30%  
3. **1w (Semanal)** - Peso: 20%

## Ejemplo de Salida - Analista Principal

```
================================================================================
🚀 ANALISTA CUANTITATIVO - DCA CON VALOR AGREGADO 🚀
================================================================================
Símbolo analizado: BTCUSDT
Inversión base: $250.00

⏰ ANÁLISIS TEMPORAL OPTIMIZADO:
   📅 Día actual: Thursday

📊 MEJOR DÍA HISTÓRICO PARA DCA (181 muestras):
   🏆 Mejor día: Thursday 🟡
   📈 Score histórico: 0.0187
   🔬 Confianza: MEDIUM

📈 RANKING HISTÓRICO DE DÍAS (últimos 6 meses):
   🥇 Thursday: Return +0.88% | Éxito 62% | (26 días)
   🥈 Wednesday: Return +0.61% | Éxito 62% | (26 días)
   🥉 Monday: Return +0.37% | Éxito 62% | (26 días)

💰 RECOMENDACIÓN DE INVERSIÓN:
   Score Cuantitativo: 0.156
   Multiplicador: 1.16x
   Cantidad recomendada: $288.97
   Recomendación: 🟡 NEUTRAL - MANTENER DCA NORMAL

📚 EXPLICACIÓN DETALLADA DE MÉTRICAS Y RANGOS DCA
============================================================
📈 1. RSI: 49.7 - Zona neutral - DCA normal
📊 2. Bollinger %B: 0.637 - Rango medio - Precio justo
[... explicaciones detalladas de todas las métricas ...]

📋 RECOMENDACIÓN FINAL DE TIMING PARA DCA
============================================================
💡 NOTA: Análisis histórico sugiere que Thursday > Lunes para DCA
   📊 Score Thursday: 0.0187
```

## Ejemplo de Salida - Backtester

```
📅 MEJORES MESES PARA DCA (Return promedio 4 semanas):
   May: 0.092 (27 muestras)
   Abr: 0.050 (25 muestras)
   
💰 COMPARACIÓN DE ESTRATEGIAS DCA:
🔹 DCA Regular (semanal):
   📈 Return total: 241.17%
   🛒 Compras realizadas: 310
   
🔹 DCA cuando RSI < 50:
   📈 Return total: 226.25%
   🛒 Compras realizadas: 116
```

## Configuración

### Cambiar Símbolo Analizado
```python
# En crypto_buy_opportunity.py
analyst = QuantitativeAnalyst(base_investment=250.0, symbol="ETHUSDT")

# En dca_timing_backtest.py  
backtester = DCATimingBacktester("ETHUSDT")
```

### Modificar Inversión Base
```python
analyst = QuantitativeAnalyst(base_investment=500.0, symbol="BTCUSDT")
```

### Personalizar Rangos DCA
```python
analyst.min_investment_multiplier = 0.3  # 30% mínimo
analyst.max_investment_multiplier = 3.0  # 300% máximo
```

## Dependencias

- `requests`: Para API de Binance
- `pandas`: Manipulación de datos
- `numpy`: Cálculos matemáticos  
- `pytz`: Manejo de zonas horarias

## Características Técnicas

### Pesos de Indicadores en Score Final
- **RSI**: 20%
- **Bollinger %B**: 15% 
- **Z-Score**: 15%
- **Volumen**: 10%
- **MACD**: 8%
- **ROC**: 7%
- **🆕 Mejor Día Histórico**: 25% (aumentado por relevancia)

### Datos de Backtesting
- **Período**: 2020-presente
- **Frecuencia**: Velas semanales
- **Símbolos**: Configurable (BTC por defecto)
- **Estrategias comparadas**: Regular, RSI, Z-Score, Bollinger

## Notas Importantes

1. **Análisis Dinámico**: El sistema identifica automáticamente el mejor día histórico (ej: Thursday actualmente)
2. **Flexibilidad Total**: Ejecuta el análisis cualquier día para recomendaciones actualizadas
3. **Datos en Tiempo Real**: Usa la API pública de Binance
4. **Sin Asesoría Financiera**: Herramienta de análisis, no asesoría de inversión
5. **Backtesting Incluido**: Analiza patrones históricos desde 2020
6. **Explicaciones Automáticas**: Cada métrica incluye guía detallada de interpretación

## Roadmap

- [x] ✅ Análisis temporal específico para lunes
- [x] ✅ Backtesting histórico completo  
- [x] ✅ Explicaciones detalladas de métricas
- [x] ✅ **Análisis del mejor día de la semana para DCA**
- [x] ✅ **Ranking histórico de días por rendimiento**
- [ ] Integración con exchange para ejecución automática
- [ ] Alertas por email/telegram
- [ ] Dashboard web interactivo
- [ ] Análisis de correlaciones entre activos

## Licencia

MIT License - Úsalo libremente pero bajo tu propio riesgo.

---

**⚠️ Disclaimer**: Este software es solo para fines educativos y de análisis. No constituye asesoría financiera. Siempre haz tu propia investigación antes de invertir. Los resultados pasados no garantizan resultados futuros.
