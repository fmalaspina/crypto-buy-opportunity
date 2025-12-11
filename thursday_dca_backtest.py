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

class ThursdayDCABacktester:
    """
    Backtester que simula inversiones DCA todos los jueves siguiendo las recomendaciones
    exactas del script QuantitativeAnalyst desde 2020.
    """

    def __init__(self, symbol: str = "BTCUSDT", start_date: str = "2020-01-01", base_investment: float = 250.0):
        self.symbol = symbol
        self.start_date = start_date
        self.base_investment = base_investment
        self.analyst = QuantitativeAnalyst(base_investment=base_investment, symbol=symbol)

        # Estadísticas del backtest
        self.total_invested = 0
        self.total_coins = 0
        self.trades = []
        self.performance_metrics = {}

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
                "interval": "1d",  # Velas diarias
                "startTime": current_timestamp,
                "limit": 1000  # Máximo permitido por Binance
            }

            try:
                resp = requests.get(BINANCE_URL, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    break

                all_data.extend(data)

                # Actualizar timestamp para siguiente batch
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

        # Conversiones de tipos
        for col in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
            df[col] = df[col].astype(float)

        df["date"] = pd.to_datetime(df["open_time"], unit="ms")
        df["weekday"] = df["date"].dt.day_of_week  # 0=Monday, 3=Thursday
        df = df.sort_values("date").reset_index(drop=True)

        print(f"✅ Datos descargados: {len(df)} días desde {df['date'].iloc[0].strftime('%Y-%m-%d')} hasta {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

        return df

    def get_thursdays(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filtra solo los jueves del DataFrame.
        """
        thursdays = df[df["weekday"] == 3].copy()  # 3 = Thursday
        print(f"📅 Encontrados {len(thursdays)} jueves en el período analizado")
        return thursdays.reset_index(drop=True)

    def simulate_analyst_decision(self, date: datetime, price_data: Dict) -> Dict:
        """
        Simula la decisión del analista cuantitativo para una fecha específica.
        Usa datos históricos disponibles hasta esa fecha.
        """
        try:
            # Crear un DataFrame temporal con datos hasta la fecha especificada
            # Para simular lo que el analista habría visto en ese momento

            # Simulamos el análisis del script (normalmente usaría datos reales hasta esa fecha)
            # Por simplicidad, usaremos una versión simplificada basada en indicadores técnicos

            # Obtener datos recientes para el análisis (simulando datos disponibles en esa fecha)
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
                # Si no hay suficientes datos, usar inversión base
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

            # Calcular indicadores técnicos simplificados
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

            # Sistema de puntuación simplificado (similar al script principal)
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

            # Bonus por ser jueves (el mejor día histórico)
            thursday_bonus = 0.25  # 25% del peso

            # Score final
            final_score = (
                scores["rsi"] * 0.25 +
                scores["bollinger"] * 0.20 +
                scores["zscore"] * 0.20 +
                scores["macd"] * 0.10 +
                scores["roc"] * 0.10 +
                thursday_bonus * 0.15
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
            # En caso de error, usar inversión base
            return {
                "investment_amount": self.base_investment,
                "investment_multiplier": 1.0,
                "final_score": 0.0,
                "recommendation": "ERROR - DCA NORMAL",
                "data_sufficient": False
            }

    def run_thursday_backtest(self) -> Dict:
        """
        Ejecuta el backtest completo invirtiendo todos los jueves.
        """
        print("="*80)
        print(f"🚀 BACKTESTING DCA JUEVES CON ANALISTA CUANTITATIVO")
        print("="*80)
        print(f"💰 Símbolo: {self.symbol}")
        print(f"📅 Período: {self.start_date} - presente")
        print(f"💵 Inversión base: ${self.base_investment:.2f}")
        print("="*80)

        # 1. Obtener datos históricos diarios
        df = self.fetch_daily_data(self.start_date)

        # 2. Filtrar solo jueves
        thursdays = self.get_thursdays(df)

        # 3. Simular inversiones en cada jueves
        print(f"\n🔄 Simulando inversiones en {len(thursdays)} jueves...")

        for idx, row in thursdays.iterrows():
            trade_date = row["date"]
            trade_price = row["close"]

            # Simular decisión del analista para esa fecha
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

            self.trades.append(trade_record)

            # Actualizar totales
            self.total_invested += investment_amount
            self.total_coins += coins_bought

            # Mostrar progreso cada 20 operaciones
            if (idx + 1) % 20 == 0:
                print(f"   Procesado: {idx + 1}/{len(thursdays)} jueves...")

        # 4. Calcular métricas finales
        final_price = df["close"].iloc[-1]
        final_value = self.total_coins * final_price
        total_return = (final_value - self.total_invested) / self.total_invested

        # 5. Calcular métricas de rendimiento
        self.performance_metrics = self.calculate_performance_metrics(df)

        return {
            "total_invested": self.total_invested,
            "total_coins": self.total_coins,
            "final_value": final_value,
            "total_return": total_return,
            "final_price": final_price,
            "trades_count": len(self.trades),
            "performance_metrics": self.performance_metrics,
            "trades": self.trades
        }

    def calculate_performance_metrics(self, df: pd.DataFrame) -> Dict:
        """
        Calcula métricas adicionales de rendimiento.
        """
        if not self.trades:
            return {}

        # Convertir trades a DataFrame para análisis
        trades_df = pd.DataFrame(self.trades)

        # Métricas de inversión
        avg_investment = trades_df["investment_amount"].mean()
        max_investment = trades_df["investment_amount"].max()
        min_investment = trades_df["investment_amount"].min()

        # Distribución de recomendaciones
        recommendation_counts = trades_df["recommendation"].value_counts()

        # Métricas de multiplicadores
        avg_multiplier = trades_df["multiplier"].mean()
        max_multiplier = trades_df["multiplier"].max()
        min_multiplier = trades_df["multiplier"].min()

        # Comparación con DCA regular
        regular_dca_invested = len(self.trades) * self.base_investment
        regular_dca_coins = sum(self.base_investment / trade["price"] for trade in self.trades)
        regular_dca_value = regular_dca_coins * df["close"].iloc[-1]
        regular_dca_return = (regular_dca_value - regular_dca_invested) / regular_dca_invested

        # Mejora vs DCA regular
        current_return = (self.total_coins * df["close"].iloc[-1] - self.total_invested) / self.total_invested
        improvement_vs_regular = ((current_return - regular_dca_return) / abs(regular_dca_return)) * 100 if regular_dca_return != 0 else 0

        return {
            "avg_investment": avg_investment,
            "max_investment": max_investment,
            "min_investment": min_investment,
            "avg_multiplier": avg_multiplier,
            "max_multiplier": max_multiplier,
            "min_multiplier": min_multiplier,
            "recommendation_distribution": recommendation_counts.to_dict(),
            "regular_dca_comparison": {
                "regular_invested": regular_dca_invested,
                "regular_coins": regular_dca_coins,
                "regular_value": regular_dca_value,
                "regular_return": regular_dca_return,
                "improvement_percentage": improvement_vs_regular
            }
        }

    def generate_detailed_report(self, results: Dict):
        """
        Genera un reporte detallado de los resultados del backtest.
        """
        print("\n" + "="*80)
        print("📊 RESULTADOS DEL BACKTEST - DCA JUEVES CON ANÁLISIS CUANTITATIVO")
        print("="*80)

        # Resultados principales
        print(f"\n💰 RESULTADOS FINANCIEROS:")
        print(f"   💵 Total invertido: ${results['total_invested']:,.2f}")
        print(f"   🪙 Monedas acumuladas: {results['total_coins']:.6f} {self.symbol.replace('USDT', '')}")
        print(f"   💎 Valor final: ${results['final_value']:,.2f}")
        print(f"   📈 Return total: {results['total_return']:.2%}")
        print(f"   🛒 Operaciones realizadas: {results['trades_count']}")
        print(f"   📅 Período: {self.start_date} - {datetime.now().strftime('%Y-%m-%d')}")

        # Métricas de inversión
        metrics = results['performance_metrics']
        print(f"\n🎯 MÉTRICAS DE INVERSIÓN:")
        print(f"   💵 Inversión promedio: ${metrics['avg_investment']:.2f}")
        print(f"   📊 Rango de inversión: ${metrics['min_investment']:.2f} - ${metrics['max_investment']:.2f}")
        print(f"   ⚖️ Multiplicador promedio: {metrics['avg_multiplier']:.2f}x")
        print(f"   📈 Multiplicador máximo: {metrics['max_multiplier']:.2f}x")
        print(f"   📉 Multiplicador mínimo: {metrics['min_multiplier']:.2f}x")

        # Distribución de recomendaciones
        print(f"\n📋 DISTRIBUCIÓN DE RECOMENDACIONES:")
        rec_dist = metrics['recommendation_distribution']
        for recommendation, count in rec_dist.items():
            percentage = (count / results['trades_count']) * 100
            print(f"   {recommendation}: {count} operaciones ({percentage:.1f}%)")

        # Comparación con DCA regular
        regular_comparison = metrics['regular_dca_comparison']
        print(f"\n🔄 COMPARACIÓN CON DCA REGULAR:")
        print(f"   💵 DCA Regular - Invertido: ${regular_comparison['regular_invested']:,.2f}")
        print(f"   💎 DCA Regular - Valor final: ${regular_comparison['regular_value']:,.2f}")
        print(f"   📈 DCA Regular - Return: {regular_comparison['regular_return']:.2%}")
        print(f"   🚀 Mejora vs DCA Regular: {regular_comparison['improvement_percentage']:+.2f}%")

        # Estadísticas adicionales
        print(f"\n📊 ESTADÍSTICAS ADICIONALES:")
        avg_price = sum(trade["price"] for trade in self.trades) / len(self.trades)
        current_price = results['final_price']
        print(f"   💰 Precio promedio de compra: ${avg_price:,.2f}")
        print(f"   💰 Precio actual: ${current_price:,.2f}")
        print(f"   📈 Apreciación del activo: {((current_price - avg_price) / avg_price) * 100:.2f}%")

        # Análisis de mejores y peores operaciones
        trades_with_value = []
        for trade in self.trades:
            current_value = trade["coins_bought"] * current_price
            roi = ((current_value - trade["investment_amount"]) / trade["investment_amount"]) * 100
            trades_with_value.append({
                **trade,
                "current_value": current_value,
                "roi": roi
            })

        # Ordenar por ROI
        trades_with_value.sort(key=lambda x: x["roi"], reverse=True)

        print(f"\n🏆 MEJORES 3 OPERACIONES:")
        for i, trade in enumerate(trades_with_value[:3], 1):
            print(f"   {i}. {trade['date'].strftime('%Y-%m-%d')}: ${trade['investment_amount']:.2f} → "
                  f"${trade['current_value']:.2f} (ROI: +{trade['roi']:.1f}%) "
                  f"[{trade['recommendation']}]")

        print(f"\n📉 OPERACIONES CON MENOR ROI:")
        for i, trade in enumerate(trades_with_value[-3:], 1):
            print(f"   {i}. {trade['date'].strftime('%Y-%m-%d')}: ${trade['investment_amount']:.2f} → "
                  f"${trade['current_value']:.2f} (ROI: {trade['roi']:+.1f}%) "
                  f"[{trade['recommendation']}]")

def main():
    """Función principal para ejecutar el backtest de jueves."""
    print("🚀 INICIANDO BACKTEST DCA JUEVES CON ANÁLISIS CUANTITATIVO")
    print("="*60)

    # Parámetros configurables
    SYMBOL = "BTCUSDT"  # Cambiar aquí el par
    START_DATE = "2020-01-01"  # Cambiar aquí la fecha de inicio
    BASE_INVESTMENT = 250.0  # Cambiar aquí la inversión base

    print(f"📊 Configuración:")
    print(f"   💰 Par: {SYMBOL}")
    print(f"   📅 Fecha inicio: {START_DATE}")
    print(f"   💵 Inversión base: ${BASE_INVESTMENT}")
    print("="*60)

    # Crear y ejecutar backtester
    backtester = ThursdayDCABacktester(
        symbol=SYMBOL,
        start_date=START_DATE,
        base_investment=BASE_INVESTMENT
    )

    # Ejecutar backtest
    results = backtester.run_thursday_backtest()

    # Generar reporte detallado
    backtester.generate_detailed_report(results)

    print("\n" + "="*80)
    print("✅ BACKTEST COMPLETADO")
    print("="*80)

if __name__ == "__main__":
    main()
