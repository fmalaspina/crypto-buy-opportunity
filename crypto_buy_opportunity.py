import warnings
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import pytz
import requests

warnings.filterwarnings('ignore')

BINANCE_URL = "https://api.binance.com/api/v3/klines"

class QuantitativeAnalyst:
    """
    Analista Cuantitativo para DCA con valor agregado.
    Analiza múltiples indicadores técnicos y patrones temporales para determinar
    el porcentaje óptimo de inversión basado en el mejor día histórico identificado automáticamente.
    """

    def __init__(self, base_investment: float = 250.0, symbol: str = "BTCUSDT"):
        self.base_investment = base_investment
        self.symbol = symbol
        self.min_investment_multiplier = 0.5  # 50% mínimo
        self.max_investment_multiplier = 2.0  # 200% máximo

    def fetch_klines(self, symbol: str, interval: str, limit: int) -> pd.DataFrame:
        """Obtiene datos de velas de Binance."""
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        resp = requests.get(BINANCE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data:
            raise ValueError(f"Sin datos para {symbol} {interval}")

        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "taker_buy_base", "taker_buy_quote", "ignore"
        ])

        # Conversiones de tipos
        for col in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
            df[col] = df[col].astype(float)

        df["date"] = pd.to_datetime(df["open_time"], unit="ms")
        df["taker_sell_base"] = df["volume"] - df["taker_buy_base"]
        df = df.sort_values("date").reset_index(drop=True)

        return df

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calcula el RSI (Relative Strength Index)."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict[str, float]:
        """Calcula Bollinger Bands y %B."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)

        current_price = prices.iloc[-1]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_sma = sma.iloc[-1]

        # %B = (Price - Lower Band) / (Upper Band - Lower Band)
        percent_b = (current_price - current_lower) / (current_upper - current_lower)

        return {
            "upper_band": current_upper,
            "lower_band": current_lower,
            "sma": current_sma,
            "percent_b": percent_b,
            "current_price": current_price
        }

    def calculate_z_score(self, prices: pd.Series, lookback: int = 20) -> float:
        """Calcula el Z-Score del precio actual vs histórico."""
        recent_prices = prices.tail(lookback)
        mean_price = recent_prices.mean()
        std_price = recent_prices.std()
        current_price = prices.iloc[-1]

        if std_price == 0:
            return 0.0

        z_score = (current_price - mean_price) / std_price
        return z_score

    def calculate_volume_profile(self, df: pd.DataFrame, lookback: int = 20) -> Dict[str, float]:
        """Analiza el perfil de volumen."""
        recent_data = df.tail(lookback)

        avg_volume = recent_data["volume"].mean()
        current_volume = df["volume"].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Análisis de presión compradora/vendedora
        avg_buy_pressure = (recent_data["taker_buy_base"] / recent_data["volume"]).mean()
        current_buy_pressure = df["taker_buy_base"].iloc[-1] / df["volume"].iloc[-1]

        buy_pressure_ratio = current_buy_pressure / avg_buy_pressure if avg_buy_pressure > 0 else 1.0

        return {
            "volume_ratio": volume_ratio,
            "current_volume": current_volume,
            "avg_volume": avg_volume,
            "buy_pressure_ratio": buy_pressure_ratio,
            "current_buy_pressure": current_buy_pressure,
            "avg_buy_pressure": avg_buy_pressure
        }

    def calculate_momentum_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calcula indicadores de momentum."""
        prices = df["close"]

        # MACD aproximado (EMA12 - EMA26)
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd_line = ema12 - ema26
        macd_signal = macd_line.ewm(span=9).mean()
        macd_histogram = macd_line - macd_signal

        # Rate of Change
        roc_period = 10
        roc = ((prices.iloc[-1] - prices.iloc[-roc_period-1]) / prices.iloc[-roc_period-1]) * 100

        return {
            "macd_line": macd_line.iloc[-1],
            "macd_signal": macd_signal.iloc[-1],
            "macd_histogram": macd_histogram.iloc[-1],
            "roc": roc
        }

    def calculate_comprehensive_score(self, symbol: str, timeframe: str = "1d") -> Dict:
        """Análisis cuantitativo completo optimizado para DCA basado en el mejor día histórico."""

        # Obtener datos suficientes para todos los cálculos
        df = self.fetch_klines(symbol, timeframe, limit=200)  # Más datos para análisis temporal

        if len(df) < 50:
            return {"error": "Datos insuficientes para análisis", "investment_multiplier": 1.0}

        prices = df["close"]

        # Calcular todos los indicadores técnicos
        rsi = self.calculate_rsi(prices)
        bb_data = self.calculate_bollinger_bands(prices)
        z_score = self.calculate_z_score(prices)
        volume_profile = self.calculate_volume_profile(df)
        momentum = self.calculate_momentum_indicators(df)

        # Análisis específico del mejor día histórico
        best_day_pattern = self.calculate_weekday_pattern_score(df.copy())
        timing_info = self.get_enhanced_timing_info()

        # Sistema de puntuación ponderado MEJORADO
        scores = {}

        # 1. RSI Score (peso: 20% - reducido por análisis temporal)
        if rsi <= 30:
            rsi_score = 1.0  # Oversold - muy bullish
        elif rsi <= 40:
            rsi_score = 0.7  # Moderadamente oversold
        elif rsi <= 60:
            rsi_score = 0.3  # Neutral
        elif rsi <= 70:
            rsi_score = -0.2  # Moderadamente overbought
        else:
            rsi_score = -0.8  # Overbought - bearish
        scores["rsi_score"] = rsi_score

        # 2. Bollinger %B Score (peso: 15%)
        percent_b = bb_data["percent_b"]
        if percent_b <= 0:
            bb_score = 1.0  # Por debajo de banda inferior
        elif percent_b <= 0.2:
            bb_score = 0.7  # Cerca de banda inferior
        elif percent_b <= 0.8:
            bb_score = 0.0  # En rango medio
        elif percent_b <= 1.0:
            bb_score = -0.3  # Cerca de banda superior
        else:
            bb_score = -0.8  # Por encima de banda superior
        scores["bb_score"] = bb_score

        # 3. Z-Score (peso: 15%)
        if z_score <= -2:
            zscore_score = 1.0  # Precio muy por debajo de la media
        elif z_score <= -1:
            zscore_score = 0.6  # Precio por debajo de la media
        elif z_score <= 1:
            zscore_score = 0.0  # Precio cerca de la media
        elif z_score <= 2:
            zscore_score = -0.4  # Precio por encima de la media
        else:
            zscore_score = -0.8  # Precio muy por encima de la media
        scores["zscore_score"] = zscore_score

        # 4. Volume Analysis (peso: 10%)
        vol_ratio = volume_profile["volume_ratio"]
        buy_pressure = volume_profile["buy_pressure_ratio"]

        volume_score = 0
        if vol_ratio >= 2.0:  # Volumen alto
            volume_score += 0.4
        elif vol_ratio >= 1.5:
            volume_score += 0.2

        if buy_pressure >= 1.2:  # Alta presión compradora
            volume_score += 0.4
        elif buy_pressure >= 1.0:
            volume_score += 0.1
        else:
            volume_score -= 0.2  # Presión vendedora

        scores["volume_score"] = volume_score

        # 5. MACD Score (peso: 8%)
        macd_histogram = momentum["macd_histogram"]
        if macd_histogram > 0 and momentum["macd_line"] < 0:
            macd_score = 0.6  # Posible reversión bullish
        elif macd_histogram > 0:
            macd_score = 0.3  # Momentum positivo
        elif macd_histogram < 0 and momentum["macd_line"] > 0:
            macd_score = -0.3  # Posible reversión bearish
        else:
            macd_score = -0.1  # Momentum negativo
        scores["macd_score"] = macd_score

        # 6. ROC Score (peso: 7%)
        roc = momentum["roc"]
        if roc < -5:
            roc_score = 0.6  # Caída fuerte = oportunidad
        elif roc < -2:
            roc_score = 0.3  # Caída moderada
        elif roc > 5:
            roc_score = -0.6  # Subida fuerte = caro
        else:
            roc_score = 0.0  # Neutral
        scores["roc_score"] = roc_score

        # 7. Mejor Día Pattern Score (peso: 25% - aumentado por ser más relevante)
        best_day_score = best_day_pattern["best_day_score"]
        scores["best_day_score"] = best_day_score

        # Cálculo del score final ponderado ACTUALIZADO
        final_score = (
            scores["rsi_score"] * 0.20 +
            scores["bb_score"] * 0.15 +
            scores["zscore_score"] * 0.15 +
            scores["volume_score"] * 0.10 +
            scores["macd_score"] * 0.08 +
            scores["roc_score"] * 0.07 +
            scores["best_day_score"] * 0.25
        )

        # Ajuste adicional por timing (si es el mejor día histórico)
        if timing_info["is_best_day_today"]:
            final_score += 0.15  # Bonus por timing óptimo

        # Convertir score a multiplicador de inversión (0.5x a 2.0x)
        investment_multiplier = 1.0 + (final_score * 1.0)  # Base + ajuste
        investment_multiplier = max(self.min_investment_multiplier,
                                   min(self.max_investment_multiplier, investment_multiplier))

        # Determinar recomendación
        if final_score >= 0.5:
            recommendation = "COMPRA FUERTE"
        elif final_score >= 0.2:
            recommendation = "COMPRA MODERADA"
        elif final_score >= -0.2:
            recommendation = "NEUTRAL"
        elif final_score >= -0.5:
            recommendation = "PRECAUCIÓN"
        else:
            recommendation = "EVITAR COMPRA"

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "final_score": final_score,
            "investment_multiplier": investment_multiplier,
            "investment_amount": self.base_investment * investment_multiplier,
            "recommendation": recommendation,
            "indicators": {
                "rsi": rsi,
                "bollinger_percent_b": percent_b,
                "z_score": z_score,
                "volume_ratio": vol_ratio,
                "buy_pressure_ratio": buy_pressure,
                "macd_histogram": macd_histogram,
                "roc": roc
            },
            "temporal_analysis": {
                "best_day_pattern": best_day_pattern,
                "timing_info": timing_info
            },
            "individual_scores": scores,
            "current_price": prices.iloc[-1],
            "timestamp": df["date"].iloc[-1]
        }

    def analyze_multiple_timeframes(self, symbol: str) -> Dict:
        """Análisis multi-timeframe para mayor precisión."""
        timeframes = ["1d", "4h", "1w"]
        results = {}
        weights = {"1d": 0.5, "4h": 0.3, "1w": 0.2}

        total_weighted_score = 0
        total_weight = 0

        for tf in timeframes:
            try:
                result = self.calculate_comprehensive_score(symbol, tf)
                if "error" not in result:
                    results[tf] = result
                    weight = weights[tf]
                    total_weighted_score += result["final_score"] * weight
                    total_weight += weight
            except Exception as e:
                print(f"Error analizando {tf}: {e}")
                continue

        if total_weight == 0:
            return {"error": "No se pudieron obtener datos para ningún timeframe"}

        # Score final combinado
        combined_score = total_weighted_score / total_weight
        combined_multiplier = 1.0 + combined_score
        combined_multiplier = max(self.min_investment_multiplier,
                                 min(self.max_investment_multiplier, combined_multiplier))

        return {
            "symbol": symbol,
            "combined_score": combined_score,
            "combined_multiplier": combined_multiplier,
            "combined_investment": self.base_investment * combined_multiplier,
            "timeframe_analysis": results,
            "base_investment": self.base_investment
        }

    def generate_report(self) -> None:
        """Genera un reporte completo de análisis cuantitativo optimizado para DCA."""

        # Información de timing mejorada
        timing_info = self.get_enhanced_timing_info()

        print("="*80)
        print("🚀 ANALISTA CUANTITATIVO - DCA CON VALOR AGREGADO 🚀")
        print("="*80)
        print(f"Símbolo analizado: {self.symbol}")
        print(f"Inversión base: ${self.base_investment:.2f}")
        print(f"Rango de inversión: ${self.base_investment * self.min_investment_multiplier:.2f} - ${self.base_investment * self.max_investment_multiplier:.2f}")

        # Información temporal mejorada
        print(f"\n⏰ ANÁLISIS TEMPORAL OPTIMIZADO:")
        print(f"   📅 Día actual: {timing_info['current_weekday']}")

        # Mostrar información del mejor día histórico
        best_day = timing_info['best_day']
        confidence = timing_info['best_day_confidence']
        confidence_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(confidence, "🟡")

        print(f"\n📊 MEJOR DÍA HISTÓRICO PARA DCA ({timing_info['total_samples']} muestras):")
        print(f"   🏆 Mejor día: {best_day} {confidence_emoji}")
        print(f"   📈 Score histórico: {timing_info['best_day_score']:.4f}")
        print(f"   🔬 Confianza: {confidence}")

        if timing_info['is_best_day_today']:
            print(f"   🎯 ¡HOY ES EL MEJOR DÍA! Momento óptimo para DCA")
        else:
            print(f"   ⏳ Próximo {best_day}: {timing_info['next_best_day'].strftime('%Y-%m-%d %H:%M UTC')}")
            print(f"   ⌛ Tiempo restante: {timing_info['hours_until_best_day']:.1f} horas")
            print(f"   🚨 Urgencia: {timing_info['best_day_urgency']}")

        # Mostrar ranking de días de la semana si hay datos
        if timing_info['weekday_analysis']:
            print(f"\n📈 RANKING HISTÓRICO DE DÍAS (últimos 6 meses):")
            # Ordenar días por score
            sorted_days = sorted(timing_info['weekday_analysis'].items(),
                               key=lambda x: x[1]['combined_score'], reverse=True)

            for i, (day, stats) in enumerate(sorted_days[:3]):  # Top 3
                position_emoji = ["🥇", "🥈", "🥉"][i]
                return_pct = stats['avg_forward_return'] * 100
                positive_rate = stats['positive_rate'] * 100
                print(f"   {position_emoji} {day}: Return +{return_pct:.2f}% | Éxito {positive_rate:.0f}% | ({stats['count']} días)")


        print("="*80)

        print(f"\n📊 ANÁLISIS DE {self.symbol}")
        print("-" * 50)

        try:
            analysis = self.analyze_multiple_timeframes(self.symbol)

            if "error" in analysis:
                print(f"❌ Error: {analysis['error']}")
                return

            # Resumen principal
            print(f"💰 RECOMENDACIÓN DE INVERSIÓN:")
            print(f"   Score Cuantitativo: {analysis['combined_score']:.3f}")
            print(f"   Multiplicador: {analysis['combined_multiplier']:.2f}x")
            print(f"   Cantidad recomendada: ${analysis['combined_investment']:.2f}")

            # Determinar recomendación general
            score = analysis['combined_score']
            if score >= 0.5:
                rec_emoji = "🟢"
                rec_text = "COMPRA FUERTE"
            elif score >= 0.2:
                rec_emoji = "🔵"
                rec_text = "COMPRA MODERADA"
            elif score >= -0.2:
                rec_emoji = "🟡"
                rec_text = "NEUTRAL - MANTENER DCA NORMAL"
            elif score >= -0.5:
                rec_emoji = "🟠"
                rec_text = "PRECAUCIÓN - REDUCIR COMPRA"
            else:
                rec_emoji = "🔴"
                rec_text = "EVITAR COMPRA"

            print(f"   Recomendación: {rec_emoji} {rec_text}")

            # Mostrar análisis temporal si está disponible (solo timeframe diario)
            if "1d" in analysis["timeframe_analysis"]:
                daily_data = analysis["timeframe_analysis"]["1d"]
                if "temporal_analysis" in daily_data:
                    temporal = daily_data["temporal_analysis"]

                    print(f"\n📈 ANÁLISIS TEMPORAL ESPECÍFICO:")
                    best_day_pattern = temporal["best_day_pattern"]

                    print(f"   🏆 Patrón del Mejor Día ({best_day_pattern['best_day']}):")
                    print(f"      • Score del mejor día: {best_day_pattern['best_day_score']:.3f}")
                    print(f"      • Return promedio: {best_day_pattern['avg_best_day_return']:.3f}")
                    print(f"      • Volatilidad relativa: {best_day_pattern['volatility_ratio']:.2f}x")


            print()

            # Sección de explicaciones detalladas de métricas
            self.print_detailed_metrics_explanation(analysis)

            # Detalles por timeframe
            for tf, data in analysis["timeframe_analysis"].items():
                print(f"📈 Timeframe {tf}:")
                indicators = data["indicators"]
                print(f"   RSI: {indicators['rsi']:.1f}")
                print(f"   Bollinger %B: {indicators['bollinger_percent_b']:.3f}")
                print(f"   Z-Score: {indicators['z_score']:.2f}")
                print(f"   Volumen relativo: {indicators['volume_ratio']:.2f}x")
                print(f"   Presión compradora: {indicators['buy_pressure_ratio']:.2f}")
                print(f"   MACD Histogram: {indicators['macd_histogram']:.4f}")
                print(f"   ROC (10d): {indicators['roc']:.2f}%")
                print(f"   Score: {data['final_score']:.3f}")

                # Mostrar scores individuales para timeframe diario
                if tf == "1d":
                    scores = data["individual_scores"]
                    print(f"   📊 Scores detallados:")
                    print(f"      RSI: {scores['rsi_score']:.2f} | BB: {scores['bb_score']:.2f} | Z: {scores['zscore_score']:.2f}")
                    print(f"      Vol: {scores['volume_score']:.2f} | MACD: {scores['macd_score']:.2f} | ROC: {scores['roc_score']:.2f}")
                    if 'best_day_score' in scores:
                        print(f"      Mejor Día: {scores['best_day_score']:.2f}")
                print()

        except Exception as e:
            print(f"❌ Error analizando {self.symbol}: {e}\n")

        # Recomendación final de timing mejorada
        print("\n" + "="*60)
        print("📋 RECOMENDACIÓN FINAL DE TIMING PARA DCA")
        print("="*60)

        # Determinar recomendación basada en el mejor día histórico
        if timing_info["is_best_day_today"]:
            print(f"🎯 ¡EJECUTAR DCA AHORA! Hoy es {timing_info['best_day']}")
            print(f"   📈 Históricamente el mejor día para comprar")
            print(f"   🔬 Confianza: {timing_info['best_day_confidence']}")
        elif timing_info["best_day_urgency"] == "INMEDIATA":
            print(f"🟡 Preparar DCA - {timing_info['best_day']} está muy cerca")
            print(f"   ⏰ {timing_info['hours_until_best_day']:.1f} horas hasta el mejor día")
        elif timing_info["best_day_urgency"] == "ALTA":
            print(f"🔵 Planificar DCA - {timing_info['best_day']} es mañana")
            print(f"   📅 El mejor día histórico se acerca")
        else:
            print(f"⏳ Monitorear - Próximo {timing_info['best_day']} en {timing_info['hours_until_best_day']:.0f}h")

        print(f"\n💡 INFORMACIÓN: Análisis histórico identifica {timing_info['best_day']} como día óptimo")
        print(f"   📊 Score histórico: {timing_info['best_day_score']:.4f}")
        print(f"   📈 Puedes ejecutar el análisis cualquier día para obtener recomendaciones actualizadas")

        print("="*60)


    def calculate_weekday_pattern_score(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Analiza el patrón histórico de rendimiento del mejor día identificado para optimizar DCA.
        Considera el comportamiento histórico del precio en diferentes días de la semana.
        """
        # Obtener información del mejor día histórico
        timing_info = self.get_enhanced_timing_info()
        best_day = timing_info['best_day']

        # Agregar día de la semana
        df['weekday'] = df['date'].dt.day_of_week  # 0=Monday, 6=Sunday
        df['weekday_name'] = df['date'].dt.day_name()

        # Mapear nombre del día a número
        weekday_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
                      'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        best_day_num = weekday_map.get(best_day, 0)

        df['is_best_day'] = df['weekday'] == best_day_num

        # Calcular returns diarios
        df['daily_return'] = df['close'].pct_change()

        # Análisis de los últimos 3 meses
        last_3_months = df[df['date'] >= (df['date'].iloc[-1] - timedelta(days=90))]

        if len(last_3_months) < 10:
            return {"best_day_score": 0.0, "pattern_strength": 0.0, "avg_best_day_return": 0.0, "best_day": best_day}

        # Estadísticas del mejor día vs otros días
        best_day_data = last_3_months[last_3_months['is_best_day']]
        other_days = last_3_months[~last_3_months['is_best_day']]

        if len(best_day_data) < 3:
            return {"best_day_score": 0.0, "pattern_strength": 0.0, "avg_best_day_return": 0.0, "best_day": best_day}

        avg_best_day_return = best_day_data['daily_return'].mean()
        avg_other_return = other_days['daily_return'].mean()

        # Análisis de volatilidad
        best_day_volatility = best_day_data['daily_return'].std()
        other_volatility = other_days['daily_return'].std()

        # Score basado en si el mejor día tiende a ser bueno para comprar
        day_advantage = avg_best_day_return - avg_other_return
        volatility_ratio = best_day_volatility / other_volatility if other_volatility > 0 else 1.0

        # Patrón de fuerza: consistencia del mejor día
        best_day_positive_rate = (best_day_data['daily_return'] > 0).mean()

        # Score final del patrón
        # Penalizamos si tiene rendimientos muy altos (indica que ya subió)
        # Premiamos si tiende a tener caídas (oportunidad de compra)
        if avg_best_day_return < -0.01:  # Caídas promedio del 1%+
            day_score = 0.4
        elif avg_best_day_return < 0:  # Caídas menores
            day_score = 0.2
        elif avg_best_day_return < 0.02:  # Subidas pequeñas
            day_score = 0.1
        else:  # Subidas grandes
            day_score = -0.2

        # Ajuste por volatilidad (más volatilidad = más oportunidad)
        if volatility_ratio > 1.2:
            day_score += 0.1
        elif volatility_ratio < 0.8:
            day_score -= 0.1

        return {
            "best_day_score": day_score,
            "pattern_strength": abs(day_advantage),
            "avg_best_day_return": avg_best_day_return,
            "best_day_volatility": best_day_volatility,
            "best_day_positive_rate": best_day_positive_rate,
            "volatility_ratio": volatility_ratio,
            "best_day": best_day
        }

    def get_time_until_next_monday(self) -> Dict[str, any]:
        """
        Calcula el tiempo hasta el próximo lunes y da recomendaciones de timing.
        """
        utc_now = datetime.now(pytz.UTC)

        # Encontrar el próximo lunes a las 9 AM UTC (aproximadamente inicio de sesión europea)
        days_until_monday = (7 - utc_now.weekday()) % 7
        if days_until_monday == 0 and utc_now.hour >= 9:
            days_until_monday = 7

        next_monday = utc_now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_until_monday)

        time_diff = next_monday - utc_now

        # Determinar urgencia del análisis
        hours_until_monday = time_diff.total_seconds() / 3600

        if hours_until_monday < 12:
            urgency = "INMEDIATA"
            timing_score = 1.0
        elif hours_until_monday < 24:
            urgency = "ALTA"
            timing_score = 0.8
        elif hours_until_monday < 48:
            urgency = "MEDIA"
            timing_score = 0.5
        else:
            urgency = "BAJA"
            timing_score = 0.2

        return {
            "next_monday": next_monday,
            "hours_until": hours_until_monday,
            "urgency": urgency,
            "timing_score": timing_score,
            "is_monday_today": utc_now.weekday() == 0 and utc_now.hour < 12
        }

    def print_detailed_metrics_explanation(self, analysis: Dict) -> None:
        """
        Imprime explicaciones detalladas de cada métrica y sus rangos para incremento de DCA.
        """
        print("\n" + "="*60)
        print("📚 EXPLICACIÓN DETALLADA DE MÉTRICAS Y RANGOS DCA")
        print("="*60)

        # Obtener datos del timeframe diario para ejemplos
        daily_data = analysis["timeframe_analysis"].get("1d", {})
        indicators = daily_data.get("indicators", {})

        # 1. RSI (Relative Strength Index)
        rsi_current = indicators.get("rsi", 50)
        print(f"\n📈 1. RSI (Relative Strength Index): {rsi_current:.1f}")
        print("   💡 QUÉ ES: Mide la fuerza del momentum, oscila entre 0-100")
        print("   🎯 INTERPRETACIÓN:")
        print("      • RSI < 30: OVERSOLD - Muy probable rebote ⬆️")
        print("      • RSI 30-40: Levemente oversold - Buena oportunidad 📈")
        print("      • RSI 40-60: Zona neutral - DCA normal 😐")
        print("      • RSI 60-70: Levemente overbought - Reducir compra 📉")
        print("      • RSI > 70: OVERBOUGHT - Evitar compra ❌")
        print("   💰 INCREMENTO DCA RECOMENDADO:")
        print("      • RSI < 30: 🟢 +80-100% (hasta 2.0x) - MÁXIMA OPORTUNIDAD")
        print("      • RSI 30-40: 🔵 +40-70% (1.4x-1.7x) - BUENA OPORTUNIDAD")
        print("      • RSI 40-60: 🟡 ±0% (1.0x) - DCA NORMAL")
        print("      • RSI 60-70: 🟠 -20% (0.8x) - REDUCIR")
        print("      • RSI > 70: 🔴 -50% (0.5x) - MÍNIMO")

        # 2. Bollinger %B
        bb_current = indicators.get("bollinger_percent_b", 0.5)
        print(f"\n📊 2. Bollinger %B: {bb_current:.3f}")
        print("   💡 QUÉ ES: Posición del precio dentro de las Bandas de Bollinger")
        print("   🎯 INTERPRETACIÓN:")
        print("      • %B ≤ 0: Precio DEBAJO banda inferior - Sobreventa extrema 🚨")
        print("      • %B 0-0.2: Cerca banda inferior - Muy barato 💎")
        print("      • %B 0.2-0.8: Rango medio - Precio justo 😐")
        print("      • %B 0.8-1.0: Cerca banda superior - Caro ⚠️")
        print("      • %B > 1.0: ARRIBA banda superior - Muy caro 🔥")
        print("   💰 INCREMENTO DCA RECOMENDADO:")
        print("      • %B ≤ 0: 🟢 +100% (2.0x) - OPORTUNIDAD EXTREMA")
        print("      • %B 0-0.2: 🔵 +70% (1.7x) - EXCELENTE ENTRADA")
        print("      • %B 0.2-0.8: 🟡 ±0% (1.0x) - DCA NORMAL")
        print("      • %B 0.8-1.0: 🟠 -30% (0.7x) - PRECAUCIÓN")
        print("      • %B > 1.0: 🔴 -50% (0.5x) - EVITAR")

        # 3. Z-Score
        zscore_current = indicators.get("z_score", 0)
        print(f"\n📉 3. Z-Score: {zscore_current:.2f}")
        print("   💡 QUÉ ES: Desviaciones estándar del precio vs media histórica")
        print("   🎯 INTERPRETACIÓN:")
        print("      • Z < -2: Precio MUY por debajo promedio - Ganga 💰")
        print("      • Z -2 a -1: Por debajo promedio - Buena compra 📈")
        print("      • Z -1 a +1: Cerca del promedio - Normal 😐")
        print("      • Z +1 a +2: Por arriba promedio - Caro ⚠️")
        print("      • Z > +2: MUY por arriba promedio - Muy caro 🔥")
        print("   💰 INCREMENTO DCA RECOMENDADO:")
        print("      • Z ≤ -2: 🟢 +100% (2.0x) - MÁXIMA DESVIACIÓN NEGATIVA")
        print("      • Z -2 a -1: 🔵 +60% (1.6x) - GRAN OPORTUNIDAD")
        print("      • Z -1 a +1: 🟡 ±0% (1.0x) - DCA NORMAL")
        print("      • Z +1 a +2: 🟠 -40% (0.6x) - REDUCIR SIGNIFICATIVAMENTE")
        print("      • Z > +2: 🔴 -50% (0.5x) - EVITAR")

        # 4. Volumen y Presión Compradora
        vol_ratio = indicators.get("volume_ratio", 1.0)
        buy_pressure = indicators.get("buy_pressure_ratio", 1.0)
        print(f"\n📊 4. ANÁLISIS DE VOLUMEN:")
        print(f"   • Volumen Relativo: {vol_ratio:.2f}x")
        print(f"   • Presión Compradora: {buy_pressure:.2f}")
        print("   💡 QUÉ ES: Detecta interés institucional y retail")
        print("   🎯 INTERPRETACIÓN:")
        print("      • Vol >2x + Presión >1.2: Alta demanda - Momentum alcista 🚀")
        print("      • Vol >1.5x + Presión >1.0: Interés moderado - Positivo 📈")
        print("      • Vol <1x o Presión <1.0: Baja demanda - Neutral/Negativo 📉")
        print("   💰 INCREMENTO DCA RECOMENDADO:")
        print("      • Vol alto + Presión alta: 🟢 +40% - Aprovechar momentum")
        print("      • Vol/Presión moderados: 🟡 ±0% - DCA normal")
        print("      • Vol/Presión bajos: 🟠 -20% - Reducir ligeramente")

        # 5. MACD Histogram
        macd_hist = indicators.get("macd_histogram", 0)
        print(f"\n⚡ 5. MACD Histogram: {macd_hist:.4f}")
        print("   💡 QUÉ ES: Diferencia entre MACD y su señal, indica momentum")
        print("   🎯 INTERPRETACIÓN:")
        print("      • MACD > 0 y creciendo: Momentum alcista creciente 🚀")
        print("      • MACD > 0 y decreciendo: Momentum alcista debilitándose ⚠️")
        print("      • MACD < 0 y creciendo: Posible reversión alcista 🔄")
        print("      • MACD < 0 y decreciendo: Momentum bajista 📉")
        print("   💰 INCREMENTO DCA RECOMENDADO:")
        print("      • MACD positivo creciente: 🟢 +30% - Momentum favorable")
        print("      • MACD cambio de negativo a positivo: 🔵 +60% - Reversión")
        print("      • MACD neutral: 🟡 ±0% - DCA normal")
        print("      • MACD negativo: 🟠 -10% - Precaución")

        # 6. ROC (Rate of Change)
        roc_current = indicators.get("roc", 0)
        print(f"\n🎢 6. ROC (10 días): {roc_current:.2f}%")
        print("   💡 QUÉ ES: Velocidad de cambio de precio en 10 períodos")
        print("   🎯 INTERPRETACIÓN:")
        print("      • ROC < -5%: Caída fuerte - Oportunidad de rebote 💎")
        print("      • ROC -5% a -2%: Caída moderada - Buena entrada 📈")
        print("      • ROC -2% a +5%: Cambio normal - Neutral 😐")
        print("      • ROC > +5%: Subida fuerte - Posible sobrecalentamiento 🔥")
        print("   💰 INCREMENTO DCA RECOMENDADO:")
        print("      • ROC < -5%: 🟢 +60% (1.6x) - REBOTE PROBABLE")
        print("      • ROC -5% a -2%: 🔵 +30% (1.3x) - APROVECHAR CAÍDA")
        print("      • ROC -2% a +5%: 🟡 ±0% (1.0x) - DCA NORMAL")
        print("      • ROC > +5%: 🔴 -60% (0.4x) - MUY CARO")

        # Patrones Temporales
        if "1d" in analysis["timeframe_analysis"] and "temporal_analysis" in analysis["timeframe_analysis"]["1d"]:
            temporal = analysis["timeframe_analysis"]["1d"]["temporal_analysis"]
            best_day_pattern = temporal["best_day_pattern"]

            print(f"\n🗓️ 7. ANÁLISIS TEMPORAL DEL MEJOR DÍA:")
            print(f"   • Score del Mejor Día ({best_day_pattern['best_day']}): {best_day_pattern['best_day_score']:.3f}")
            print("   💡 QUÉ ES: Análisis histórico del día de la semana más favorable para DCA")
            print("   🎯 INTERPRETACIÓN:")
            print(f"      • El sistema identifica automáticamente el mejor día histórico")
            print(f"      • Analiza patrones de los últimos 6 meses para encontrar oportunidades")
            print(f"      • Score > 0.2: Día históricamente favorable para comprar")
            print(f"      • Score < -0.2: Día históricamente desfavorable")
            print("   💰 INCREMENTO DCA RECOMENDADO:")
            print("      • Score > 0.3: 🟢 +40% - TIMING EXCELENTE")
            print("      • Score 0.1-0.3: 🔵 +20% - BUEN TIMING")
            print("      • Score -0.1-0.1: 🟡 ±0% - TIMING NEUTRAL")
            print("      • Score < -0.1: 🟠 -20% - TIMING DESFAVORABLE")

        print("\n" + "="*60)
        print("🎯 ESTRATEGIA FINAL DE INCREMENTO DCA")
        print("="*60)
        score = analysis['combined_score']
        multiplier = analysis['combined_multiplier']
        investment = analysis['combined_investment']

        print(f"📊 Score Cuantitativo Final: {score:.3f}")
        print(f"💰 Multiplicador Calculado: {multiplier:.2f}x")
        print(f"💵 Inversión Recomendada: ${investment:.2f}")

        print(f"\n🧮 LÓGICA DE CÁLCULO:")
        print(f"   • Score > +0.5: Incremento hasta 100% (máximo 2.0x)")
        print(f"   • Score +0.2 a +0.5: Incremento 20%-50% (1.2x-1.5x)")
        print(f"   • Score -0.2 a +0.2: Inversión normal (1.0x)")
        print(f"   • Score -0.5 a -0.2: Reducción 10%-20% (0.8x-0.9x)")
        print(f"   • Score < -0.5: Reducción hasta 50% (mínimo 0.5x)")

        print(f"\n⚖️ PESOS DE CADA INDICADOR EN EL SCORE FINAL:")
        print(f"   • RSI: 20% | Bollinger %B: 15% | Z-Score: 15%")
        print(f"   • Volumen: 10% | MACD: 8% | ROC: 7%")
        print(f"   • Mejor Día Histórico: 25%")

    def calculate_best_weekday_analysis(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Analiza qué día de la semana es históricamente mejor para comprar.
        """
        # Agregar día de la semana
        df['weekday'] = df['date'].dt.day_of_week  # 0=Monday, 6=Sunday
        df['weekday_name'] = df['date'].dt.day_name()

        # Calcular returns forward (siguiente período)
        df['forward_return'] = df['close'].pct_change(periods=-1)

        # Análisis de los últimos 6 meses
        last_6_months = df[df['date'] >= (df['date'].iloc[-1] - timedelta(days=180))]

        if len(last_6_months) < 30:
            return {
                "best_day": "Monday",
                "best_day_score": 0.0,
                "weekday_analysis": {},
                "confidence": "LOW"
            }

        # Análisis por día de semana
        weekday_stats = {}
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        for day_num, day_name in enumerate(weekday_names):
            day_data = last_6_months[last_6_months['weekday'] == day_num]

            if len(day_data) < 3:
                continue

            avg_forward_return = day_data['forward_return'].mean()
            positive_rate = (day_data['forward_return'] > 0).mean()
            volatility = day_data['forward_return'].std()
            count = len(day_data)

            # Score combinado: return promedio + tasa positiva - volatilidad/10
            combined_score = avg_forward_return + positive_rate * 0.02 - volatility * 0.1

            weekday_stats[day_name] = {
                'avg_forward_return': avg_forward_return,
                'positive_rate': positive_rate,
                'volatility': volatility,
                'count': count,
                'combined_score': combined_score
            }

        if not weekday_stats:
            return {
                "best_day": "Monday",
                "best_day_score": 0.0,
                "weekday_analysis": {},
                "confidence": "LOW"
            }

        # Encontrar el mejor día
        best_day = max(weekday_stats.keys(), key=lambda day: weekday_stats[day]['combined_score'])
        best_score = weekday_stats[best_day]['combined_score']

        # Determinar confianza basada en cantidad de datos y consistencia
        total_samples = sum([stats['count'] for stats in weekday_stats.values()])
        score_std = pd.Series([stats['combined_score'] for stats in weekday_stats.values()]).std()

        if total_samples > 100 and score_std > 0.01:
            confidence = "HIGH"
        elif total_samples > 50:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return {
            "best_day": best_day,
            "best_day_score": best_score,
            "weekday_analysis": weekday_stats,
            "confidence": confidence,
            "total_samples": total_samples
        }

    def get_enhanced_timing_info(self) -> Dict[str, any]:
        """
        Información de timing mejorada que incluye análisis del mejor día de la semana.
        """
        utc_now = datetime.now(pytz.UTC)
        current_weekday = utc_now.strftime('%A')

        # Análisis básico de lunes
        basic_timing = self.get_time_until_next_monday()

        # Obtener datos para análisis de mejor día
        try:
            df = self.fetch_klines(self.symbol, "1d", limit=200)
            best_day_analysis = self.calculate_best_weekday_analysis(df.copy())
        except:
            best_day_analysis = {
                "best_day": "Monday",
                "best_day_score": 0.0,
                "weekday_analysis": {},
                "confidence": "LOW"
            }

        # Calcular días hasta el mejor día identificado
        best_day = best_day_analysis["best_day"]
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        current_day_num = utc_now.weekday()  # 0=Monday
        best_day_num = weekdays.index(best_day)

        days_until_best = (best_day_num - current_day_num) % 7
        if days_until_best == 0:
            # Si hoy es el mejor día, no necesitamos esperar
            days_until_best = 0

        if days_until_best == 0:
            # Si es hoy, calcular horas hasta el final del día
            next_best_day = utc_now.replace(hour=23, minute=59, second=59, microsecond=0)
        else:
            next_best_day = utc_now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_until_best)

        hours_until_best = (next_best_day - utc_now).total_seconds() / 3600

        # Determinar urgencia para el mejor día
        if days_until_best == 0:
            # Si hoy es el mejor día
            best_day_urgency = "INMEDIATA"
        elif hours_until_best < 12:
            best_day_urgency = "INMEDIATA"
        elif hours_until_best < 24:
            best_day_urgency = "ALTA"
        elif hours_until_best < 48:
            best_day_urgency = "MEDIA"
        else:
            best_day_urgency = "BAJA"

        # Comparar si estamos en el mejor día vs lunes
        is_best_day_today = current_weekday == best_day
        is_monday_better = best_day == "Monday"

        return {
            **basic_timing,  # Incluir info básica de lunes
            "best_day": best_day,
            "best_day_score": best_day_analysis["best_day_score"],
            "best_day_confidence": best_day_analysis["confidence"],
            "current_weekday": current_weekday,
            "is_best_day_today": is_best_day_today,
            "is_monday_better": is_monday_better,
            "hours_until_best_day": hours_until_best,
            "best_day_urgency": best_day_urgency,
            "next_best_day": next_best_day,
            "weekday_analysis": best_day_analysis["weekday_analysis"],
            "total_samples": best_day_analysis.get("total_samples", 0)
        }


def main():
    """Función principal."""
    # Crear instancia del analista con BTC por defecto
    analyst = QuantitativeAnalyst(base_investment=250.0, symbol="BTCUSDT")

    # Generar reporte para el símbolo configurado
    analyst.generate_report()


if __name__ == "__main__":
    main()
