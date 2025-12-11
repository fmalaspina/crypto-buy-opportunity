import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
from typing import Dict, List, Tuple
import sys
import os

# Agregar el directorio actual al path para importar el script principal
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from crypto_buy_opportunity import QuantitativeAnalyst

warnings.filterwarnings('ignore')

BINANCE_URL = "https://api.binance.com/api/v3/klines"

class SundayDCAComparison:
    """
    Compara DCA regular todos los domingos vs DCA con análisis cuantitativo todos los domingos.
    """

    def __init__(self, symbol: str = "BTCUSDT", start_date: str = "2020-01-01", base_investment: float = 250.0):
        self.symbol = symbol
        self.start_date = start_date
        self.base_investment = base_investment
        self.analyst = QuantitativeAnalyst(base_investment=base_investment, symbol=symbol)

    def fetch_daily_data(self, start_date: str = "2020-01-01") -> pd.DataFrame:
        """
        Obtiene datos históricos diarios desde la fecha especificada.
        """
        print(f"📊 Descargando datos diarios de {self.symbol} desde {start_date}...")

        # Convertir fecha a timestamp
        start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)

        all_data = []
        current_timestamp = start_timestamp

        while current_timestamp < int(datetime.now().timestamp() * 1000):
            params = {
                "symbol": self.symbol,
                "interval": "1d",
                "startTime": current_timestamp,
                "limit": 1000
            }

            try:
                resp = requests.get(BINANCE_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                all_data.extend(data)
                last_timestamp = data[-1][6]  # close_time
                current_timestamp = last_timestamp + 1

                if len(all_data) % 1000 == 0:
                    print(f"   Descargado: {len(all_data)} días...")

            except Exception as e:
                print(f"   Error descargando datos: {e}")
                break

        if not all_data:
            raise ValueError(f"No se pudieron obtener datos históricos para {self.symbol}")

        # Crear DataFrame
        df = pd.DataFrame(all_data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "taker_buy_base", "taker_buy_quote", "ignore"
        ])

        for col in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
            df[col] = df[col].astype(float)

        df["date"] = pd.to_datetime(df["open_time"], unit="ms")
        df["weekday"] = df["date"].dt.day_of_week  # 0=Monday, 6=Sunday
        df = df.sort_values("date").reset_index(drop=True)

        print(f"✅ Datos descargados: {len(df)} días desde {df['date'].iloc[0].strftime('%Y-%m-%d')} hasta {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
        return df

    def get_sundays(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra solo los domingos del DataFrame.
        """
        sundays = df[df["weekday"] == 6].copy()  # 6 = Sunday
        print(f"📅 Encontrados {len(sundays)} domingos en el período analizado")
        return sundays.reset_index(drop=True)

    def simulate_analyst_decision(self, date: datetime, price_data: Dict) -> Dict:
        """
        Simula la decisión del analista cuantitativo para una fecha específica.
        Versión optimizada para domingos.
        """
        try:
            # Obtener datos históricos hasta la fecha especificada
            end_timestamp = int(date.timestamp() * 1000)
            start_timestamp = end_timestamp - (200 * 24 * 60 * 60 * 1000)  # 200 días hacia atrás

            params = {
                "symbol": self.symbol,
                "interval": "1d",
                "startTime": start_timestamp,
                "endTime": end_timestamp,
                "limit": 200
            }

            resp = requests.get(BINANCE_URL, params=params, timeout=10)
            resp.raise_for_status()
            historical_data = resp.json()

            if not historical_data or len(historical_data) < 50:
                return {
                    "investment_amount": self.base_investment,
                    "investment_multiplier": 1.0,
                    "final_score": 0.0,
                    "recommendation": "NEUTRAL",
                    "data_sufficient": False
                }

            # Crear DataFrame temporal
            temp_df = pd.DataFrame(historical_data, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "qav", "num_trades", "taker_buy_base", "taker_buy_quote", "ignore"
            ])

            for col in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
                temp_df[col] = temp_df[col].astype(float)

            temp_df["date"] = pd.to_datetime(temp_df["open_time"], unit="ms")

            # Calcular indicadores técnicos
            prices = temp_df["close"]

            # RSI
            delta = prices.diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = rsi.iloc[-1]

            # Bollinger Bands %B
            sma = prices.rolling(window=20).mean()
            std_dev = prices.rolling(window=20).std()
            upper_band = sma + (2 * std_dev)
            lower_band = sma - (2 * std_dev)
            current_price = prices.iloc[-1]
            bb_percent = (current_price - lower_band.iloc[-1]) / (upper_band.iloc[-1] - lower_band.iloc[-1])

            # Z-Score
            recent_prices = prices.tail(20)
            mean_price = recent_prices.mean()
            std_price = recent_prices.std()
            z_score = (current_price - mean_price) / std_price if std_price > 0 else 0

            # MACD
            ema12 = prices.ewm(span=12).mean()
            ema26 = prices.ewm(span=26).mean()
            macd_line = ema12 - ema26
            macd_signal = macd_line.ewm(span=9).mean()
            macd_histogram = macd_line.iloc[-1] - macd_signal.iloc[-1]

            # ROC
            roc = ((prices.iloc[-1] - prices.iloc[-11]) / prices.iloc[-11]) * 100

            # Sistema de puntuación
            scores = {}

            # RSI Score
            if current_rsi <= 30:
                rsi_score = 1.0
            elif current_rsi <= 40:
                rsi_score = 0.7
            elif current_rsi <= 60:
                rsi_score = 0.3
            elif current_rsi <= 70:
                rsi_score = -0.2
            else:
                rsi_score = -0.8
            scores["rsi"] = rsi_score

            # Bollinger %B Score
            if bb_percent <= 0:
                bb_score = 1.0
            elif bb_percent <= 0.2:
                bb_score = 0.7
            elif bb_percent <= 0.8:
                bb_score = 0.0
            elif bb_percent <= 1.0:
                bb_score = -0.3
            else:
                bb_score = -0.8
            scores["bollinger"] = bb_score

            # Z-Score Score
            if z_score <= -2:
                zscore_score = 1.0
            elif z_score <= -1:
                zscore_score = 0.6
            elif z_score <= 1:
                zscore_score = 0.0
            elif z_score <= 2:
                zscore_score = -0.4
            else:
                zscore_score = -0.8
            scores["zscore"] = zscore_score

            # MACD Score
            if macd_histogram > 0:
                macd_score = 0.3
            else:
                macd_score = -0.1
            scores["macd"] = macd_score

            # ROC Score
            if roc < -5:
                roc_score = 0.6
            elif roc < -2:
                roc_score = 0.3
            elif roc > 5:
                roc_score = -0.6
            else:
                roc_score = 0.0
            scores["roc"] = roc_score

            # Bonus por ser domingo (mejor día histórico según backtest)
            sunday_bonus = 0.30  # 30% del peso - aumentado porque domingo es el mejor

            # Score final
            final_score = (
                scores["rsi"] * 0.25 +
                scores["bollinger"] * 0.20 +
                scores["zscore"] * 0.20 +
                scores["macd"] * 0.10 +
                scores["roc"] * 0.10 +
                sunday_bonus * 0.15
            )

            # Convertir score a multiplicador
            investment_multiplier = 1.0 + final_score
            investment_multiplier = max(0.5, min(2.0, investment_multiplier))

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
                "investment_amount": self.base_investment * investment_multiplier,
                "investment_multiplier": investment_multiplier,
                "final_score": final_score,
                "recommendation": recommendation,
                "data_sufficient": True,
                "indicators": {
                    "rsi": current_rsi,
                    "bb_percent": bb_percent,
                    "z_score": z_score,
                    "macd_histogram": macd_histogram,
                    "roc": roc
                },
                "scores": scores
            }

        except Exception as e:
            print(f"   Error simulando análisis para {date.strftime('%Y-%m-%d')}: {e}")
            return {
                "investment_amount": self.base_investment,
                "investment_multiplier": 1.0,
                "final_score": 0.0,
                "recommendation": "ERROR - DCA NORMAL",
                "data_sufficient": False
            }

    def run_sunday_comparison(self) -> Dict:
        """
        Ejecuta la comparación completa entre DCA regular y DCA con análisis en domingos.
        """
        print("="*80)
        print("🔥 COMPARACIÓN: DCA DOMINGOS REGULAR vs CON ANÁLISIS CUANTITATIVO")
        print("="*80)
        print(f"💰 Símbolo: {self.symbol}")
        print(f"📅 Período: {self.start_date} - presente")
        print(f"💵 Inversión base: ${self.base_investment:.2f}")
        print("="*80)

        # 1. Obtener datos históricos
        df = self.fetch_daily_data(self.start_date)
        sundays = self.get_sundays(df)

        # 2. Simular DCA regular todos los domingos
        print(f"\n📈 Simulando DCA REGULAR todos los domingos...")
        regular_total_invested = 0
        regular_total_coins = 0

        for _, row in sundays.iterrows():
            regular_total_invested += self.base_investment
            coins_bought = self.base_investment / row["close"]
            regular_total_coins += coins_bought

        regular_final_value = regular_total_coins * df["close"].iloc[-1]
        regular_return = (regular_final_value - regular_total_invested) / regular_total_invested

        # 3. Simular DCA con análisis todos los domingos
        print(f"\n🤖 Simulando DCA CON ANÁLISIS todos los domingos...")
        analysis_trades = []
        analysis_total_invested = 0
        analysis_total_coins = 0

        for idx, row in sundays.iterrows():
            trade_date = row["date"]
            trade_price = row["close"]

            # Simular decisión del analista
            analysis = self.simulate_analyst_decision(trade_date, row)

            # Realizar la "compra"
            investment_amount = analysis["investment_amount"]
            coins_bought = investment_amount / trade_price

            # Registrar operación
            trade_record = {
                "date": trade_date,
                "price": trade_price,
                "investment_amount": investment_amount,
                "coins_bought": coins_bought,
                "multiplier": analysis["investment_multiplier"],
                "score": analysis["final_score"],
                "recommendation": analysis["recommendation"],
                "data_sufficient": analysis["data_sufficient"]
            }

            if analysis["data_sufficient"]:
                trade_record.update({
                    "rsi": analysis["indicators"]["rsi"],
                    "bb_percent": analysis["indicators"]["bb_percent"],
                    "z_score": analysis["indicators"]["z_score"],
                    "macd_histogram": analysis["indicators"]["macd_histogram"],
                    "roc": analysis["indicators"]["roc"]
                })

            analysis_trades.append(trade_record)
            analysis_total_invested += investment_amount
            analysis_total_coins += coins_bought

            # Mostrar progreso
            if (idx + 1) % 20 == 0:
                print(f"   Procesado: {idx + 1}/{len(sundays)} domingos...")

        analysis_final_value = analysis_total_coins * df["close"].iloc[-1]
        analysis_return = (analysis_final_value - analysis_total_invested) / analysis_total_invested

        # 4. Calcular métricas comparativas
        results = {
            "regular_dca": {
                "total_invested": regular_total_invested,
                "total_coins": regular_total_coins,
                "final_value": regular_final_value,
                "total_return": regular_return,
                "operations": len(sundays),
                "avg_investment": self.base_investment
            },
            "analysis_dca": {
                "total_invested": analysis_total_invested,
                "total_coins": analysis_total_coins,
                "final_value": analysis_final_value,
                "total_return": analysis_return,
                "operations": len(analysis_trades),
                "avg_investment": analysis_total_invested / len(analysis_trades),
                "trades": analysis_trades
            },
            "comparison": {
                "return_difference": analysis_return - regular_return,
                "return_improvement": ((analysis_return - regular_return) / abs(regular_return)) * 100,
                "capital_difference": analysis_total_invested - regular_total_invested,
                "capital_efficiency": (analysis_return / (analysis_total_invested / regular_total_invested)) / regular_return - 1,
                "final_price": df["close"].iloc[-1],
                "period_years": (df["date"].iloc[-1] - df["date"].iloc[0]).days / 365.25
            }
        }

        return results

    def generate_detailed_report(self, results: Dict):
        """
        Genera un reporte detallado de la comparación.
        """
        print("\n" + "="*80)
        print("📊 RESULTADOS COMPARATIVOS - DOMINGOS REGULAR vs ANÁLISIS")
        print("="*80)

        regular = results["regular_dca"]
        analysis = results["analysis_dca"]
        comparison = results["comparison"]

        # Resultados lado a lado
        print(f"\n📈 DCA REGULAR DOMINGOS:")
        print(f"   💵 Total invertido: ${regular['total_invested']:,.2f}")
        print(f"   🪙 Monedas acumuladas: {regular['total_coins']:.6f} {self.symbol.replace('USDT', '')}")
        print(f"   💎 Valor final: ${regular['final_value']:,.2f}")
        print(f"   📈 Return total: {regular['total_return']:.2%}")
        print(f"   🛒 Operaciones: {regular['operations']}")
        print(f"   💰 Inversión promedio: ${regular['avg_investment']:.2f}")

        print(f"\n🤖 DCA CON ANÁLISIS DOMINGOS:")
        print(f"   💵 Total invertido: ${analysis['total_invested']:,.2f}")
        print(f"   🪙 Monedas acumuladas: {analysis['total_coins']:.6f} {self.symbol.replace('USDT', '')}")
        print(f"   💎 Valor final: ${analysis['final_value']:,.2f}")
        print(f"   📈 Return total: {analysis['total_return']:.2%}")
        print(f"   🛒 Operaciones: {analysis['operations']}")
        print(f"   💰 Inversión promedio: ${analysis['avg_investment']:.2f}")

        # Diferencias clave
        print(f"\n🔍 DIFERENCIAS CLAVE:")
        print(f"   📊 Diferencia en return: {comparison['return_difference']:+.2%}")
        print(f"   📈 Mejora porcentual: {comparison['return_improvement']:+.2f}%")
        print(f"   💵 Diferencia de capital: ${comparison['capital_difference']:+,.2f}")
        print(f"   ⚖️ Factor de capital usado: {analysis['total_invested']/regular['total_invested']:.2f}x")

        # Eficiencia ajustada por capital
        if comparison['capital_difference'] > 0:
            print(f"   🎯 Return ajustado por capital extra: {(analysis['total_return'] - (comparison['capital_difference']/regular['total_invested']) * regular['total_return']):.2%}")

        # Distribución de recomendaciones del análisis
        if analysis['trades']:
            trades_df = pd.DataFrame(analysis['trades'])
            rec_distribution = trades_df['recommendation'].value_counts()
            print(f"\n📋 DISTRIBUCIÓN DE RECOMENDACIONES (ANÁLISIS):")
            for recommendation, count in rec_distribution.items():
                percentage = (count / len(analysis['trades'])) * 100
                print(f"   {recommendation}: {count} ({percentage:.1f}%)")

            # Mejores operaciones del análisis
            trades_with_value = []
            for trade in analysis['trades']:
                current_value = trade["coins_bought"] * comparison['final_price']
                roi = ((current_value - trade["investment_amount"]) / trade["investment_amount"]) * 100
                trades_with_value.append({**trade, "current_value": current_value, "roi": roi})

            trades_with_value.sort(key=lambda x: x["roi"], reverse=True)

            print(f"\n🏆 MEJORES 3 OPERACIONES (ANÁLISIS):")
            for i, trade in enumerate(trades_with_value[:3], 1):
                print(f"   {i}. {trade['date'].strftime('%Y-%m-%d')}: ${trade['investment_amount']:.2f} → "
                      f"${trade['current_value']:.2f} (ROI: +{trade['roi']:.1f}%) "
                      f"[{trade['recommendation']}]")

        # Conclusión
        print(f"\n" + "="*50)
        print("🎯 CONCLUSIÓN DOMINICAL")
        print("="*50)

        if comparison['return_improvement'] > 2:
            print(f"✅ EL ANÁLISIS AGREGA VALOR SIGNIFICATIVO")
            print(f"📈 Mejora de {comparison['return_improvement']:+.1f}% justifica la complejidad")
        elif comparison['return_improvement'] > 0:
            print(f"🟡 EL ANÁLISIS AGREGA VALOR MARGINAL")
            print(f"📊 Mejora de {comparison['return_improvement']:+.1f}% es pequeña pero positiva")
        else:
            print(f"❌ EL ANÁLISIS NO AGREGA VALOR")
            print(f"📉 Pérdida de {comparison['return_improvement']:+.1f}% vs DCA simple")

        # Recomendación específica para domingos
        print(f"\n💡 RECOMENDACIÓN PARA DOMINGOS:")
        if abs(comparison['return_improvement']) < 1:
            print("   🤷‍♂️ Las diferencias son mínimas (<1%)")
            print("   ⚡ Usar DCA regular domingo por simplicidad")
            print("   💡 O usar análisis si prefieres control granular")
        elif comparison['return_improvement'] > 1:
            print("   ✅ Usar DCA con análisis los domingos")
            print("   🎯 El análisis mejora significativamente los resultados")
        else:
            print("   🚨 Evitar análisis los domingos")
            print("   📈 DCA regular simple funciona mejor")

def main():
    """Función principal para la comparación de domingos."""
    print("🔥 INICIANDO COMPARACIÓN: DCA DOMINGOS REGULAR vs ANÁLISIS")
    print("="*60)

    # Parámetros
    SYMBOL = "BTCUSDT"
    START_DATE = "2020-01-01"
    BASE_INVESTMENT = 250.0

    print(f"📊 Configuración:")
    print(f"   💰 Par: {SYMBOL}")
    print(f"   📅 Fecha inicio: {START_DATE}")
    print(f"   💵 Inversión base: ${BASE_INVESTMENT}")
    print("="*60)

    # Crear y ejecutar comparador
    comparator = SundayDCAComparison(
        symbol=SYMBOL,
        start_date=START_DATE,
        base_investment=BASE_INVESTMENT
    )

    # Ejecutar comparación
    results = comparator.run_sunday_comparison()

    # Generar reporte
    comparator.generate_detailed_report(results)

    print("\n" + "="*80)
    print("✅ COMPARACIÓN DOMINICAL COMPLETADA")
    print("="*80)

if __name__ == "__main__":
    main()
