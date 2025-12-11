import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
from typing import Dict, List, Tuple
warnings.filterwarnings('ignore')

BINANCE_URL = "https://api.binance.com/api/v3/klines"

class DCATimingBacktester:
    """
    Analizador de backtesting para identificar los mejores momentos históricos para DCA.
    Analiza datos desde 2020 con velas semanales para encontrar patrones optimales.
    """

    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol
        self.base_investment = 100  # $100 por semana para el backtest

    def fetch_historical_data(self, start_date: str = "2020-01-01") -> pd.DataFrame:
        """
        Obtiene datos históricos semanales desde la fecha especificada.
        """
        print(f"📊 Descargando datos históricos de {self.symbol} desde {start_date}...")

        # Convertir fecha a timestamp
        start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)

        all_data = []
        current_timestamp = start_timestamp

        while current_timestamp < int(datetime.now().timestamp() * 1000):
            params = {
                "symbol": self.symbol,
                "interval": "1w",  # Velas semanales
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

                print(f"   Descargado hasta: {datetime.fromtimestamp(last_timestamp/1000).strftime('%Y-%m-%d')}")

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
        df = df.sort_values("date").reset_index(drop=True)

        print(f"✅ Datos descargados: {len(df)} velas semanales desde {df['date'].iloc[0].strftime('%Y-%m-%d')} hasta {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

        return df

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos para el análisis de backtesting.
        """
        print("🔧 Calculando indicadores técnicos...")

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['bb_std'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma_20'] + (2 * df['bb_std'])
        df['bb_lower'] = df['sma_20'] - (2 * df['bb_std'])
        df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # Z-Score (20 períodos)
        df['z_score'] = (df['close'] - df['close'].rolling(window=20).mean()) / df['close'].rolling(window=20).std()

        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # Returns para análisis
        df['weekly_return'] = df['close'].pct_change()
        df['forward_return_1w'] = df['close'].pct_change(periods=-1)  # Return de la siguiente semana
        df['forward_return_4w'] = df['close'].pct_change(periods=-4)  # Return a 4 semanas
        df['forward_return_12w'] = df['close'].pct_change(periods=-12)  # Return a 12 semanas

        # Análisis temporal
        df['week_of_year'] = df['date'].dt.isocalendar().week
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['year'] = df['date'].dt.year

        return df

    def analyze_timing_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Analiza patrones temporales para identificar los mejores momentos para DCA.
        """
        print("📈 Analizando patrones temporales...")

        results = {}

        # 1. Análisis por semana del año
        weekly_analysis = df.groupby('week_of_year').agg({
            'forward_return_4w': ['mean', 'median', 'std', 'count'],
            'forward_return_12w': ['mean', 'median', 'std'],
            'rsi': 'mean',
            'bb_percent_b': 'mean',
            'z_score': 'mean'
        }).round(4)

        weekly_analysis.columns = ['_'.join(col).strip() for col in weekly_analysis.columns]
        weekly_analysis = weekly_analysis.reset_index()

        # Identificar mejores semanas (mayor return forward promedio)
        best_weeks_4w = weekly_analysis.nlargest(5, 'forward_return_4w_mean')
        worst_weeks_4w = weekly_analysis.nsmallest(5, 'forward_return_4w_mean')

        results['weekly_patterns'] = {
            'full_data': weekly_analysis,
            'best_weeks_4w': best_weeks_4w,
            'worst_weeks_4w': worst_weeks_4w
        }

        # 2. Análisis por mes
        monthly_analysis = df.groupby('month').agg({
            'forward_return_4w': ['mean', 'median', 'std', 'count'],
            'forward_return_12w': ['mean', 'median', 'std'],
            'rsi': 'mean',
            'bb_percent_b': 'mean'
        }).round(4)

        monthly_analysis.columns = ['_'.join(col).strip() for col in monthly_analysis.columns]
        monthly_analysis = monthly_analysis.reset_index()

        results['monthly_patterns'] = monthly_analysis

        # 3. Análisis por trimestre
        quarterly_analysis = df.groupby('quarter').agg({
            'forward_return_4w': ['mean', 'median', 'std', 'count'],
            'forward_return_12w': ['mean', 'median', 'std'],
            'rsi': 'mean'
        }).round(4)

        quarterly_analysis.columns = ['_'.join(col).strip() for col in quarterly_analysis.columns]
        results['quarterly_patterns'] = quarterly_analysis.reset_index()

        return results

    def analyze_technical_entry_points(self, df: pd.DataFrame) -> Dict:
        """
        Analiza los mejores puntos de entrada basados en indicadores técnicos.
        """
        print("🎯 Analizando puntos de entrada técnicos...")

        # Filtrar datos válidos (sin NaN)
        valid_data = df.dropna(subset=['rsi', 'bb_percent_b', 'z_score', 'forward_return_4w'])

        results = {}

        # 1. Análisis por rangos de RSI
        rsi_bins = [0, 30, 40, 50, 60, 70, 100]
        rsi_labels = ['Oversold(<30)', 'Low(30-40)', 'Neutral-Low(40-50)',
                     'Neutral-High(50-60)', 'High(60-70)', 'Overbought(>70)']

        valid_data['rsi_range'] = pd.cut(valid_data['rsi'], bins=rsi_bins, labels=rsi_labels)

        rsi_analysis = valid_data.groupby('rsi_range').agg({
            'forward_return_4w': ['mean', 'median', 'std', 'count'],
            'forward_return_12w': ['mean', 'median', 'std']
        }).round(4)

        rsi_analysis.columns = ['_'.join(col).strip() for col in rsi_analysis.columns]
        results['rsi_analysis'] = rsi_analysis.reset_index()

        # 2. Análisis por rangos de Bollinger %B
        bb_bins = [-0.5, 0, 0.2, 0.8, 1.0, 1.5]
        bb_labels = ['Below(-0.5-0)', 'Lower(0-0.2)', 'Middle(0.2-0.8)', 'Upper(0.8-1.0)', 'Above(>1.0)']

        valid_data['bb_range'] = pd.cut(valid_data['bb_percent_b'], bins=bb_bins, labels=bb_labels)

        bb_analysis = valid_data.groupby('bb_range').agg({
            'forward_return_4w': ['mean', 'median', 'std', 'count'],
            'forward_return_12w': ['mean', 'median', 'std']
        }).round(4)

        bb_analysis.columns = ['_'.join(col).strip() for col in bb_analysis.columns]
        results['bb_analysis'] = bb_analysis.reset_index()

        # 3. Análisis por rangos de Z-Score
        zscore_bins = [-5, -2, -1, 0, 1, 2, 5]
        zscore_labels = ['Very Low(<-2)', 'Low(-2 to -1)', 'Slightly Low(-1 to 0)',
                        'Slightly High(0 to 1)', 'High(1 to 2)', 'Very High(>2)']

        valid_data['zscore_range'] = pd.cut(valid_data['z_score'], bins=zscore_bins, labels=zscore_labels)

        zscore_analysis = valid_data.groupby('zscore_range').agg({
            'forward_return_4w': ['mean', 'median', 'std', 'count'],
            'forward_return_12w': ['mean', 'median', 'std']
        }).round(4)

        zscore_analysis.columns = ['_'.join(col).strip() for col in zscore_analysis.columns]
        results['zscore_analysis'] = zscore_analysis.reset_index()

        return results

    def simulate_dca_strategies(self, df: pd.DataFrame) -> Dict:
        """
        Simula diferentes estrategias de DCA basadas en los indicadores.
        """
        print("💰 Simulando estrategias DCA...")

        strategies = {}

        # Estrategia 1: DCA Regular (todas las semanas)
        regular_dca = self.simulate_regular_dca(df)
        strategies['regular_dca'] = regular_dca

        # Estrategia 2: DCA basado en RSI (solo cuando RSI < 50)
        rsi_dca = self.simulate_conditional_dca(df, condition='rsi', threshold=50, operator='<')
        strategies['rsi_based_dca'] = rsi_dca

        # Estrategia 3: DCA basado en Z-Score (solo cuando Z-Score < -0.5)
        zscore_dca = self.simulate_conditional_dca(df, condition='z_score', threshold=-0.5, operator='<')
        strategies['zscore_based_dca'] = zscore_dca

        # Estrategia 4: DCA basado en Bollinger %B (solo cuando %B < 0.3)
        bb_dca = self.simulate_conditional_dca(df, condition='bb_percent_b', threshold=0.3, operator='<')
        strategies['bollinger_based_dca'] = bb_dca

        return strategies

    def simulate_regular_dca(self, df: pd.DataFrame) -> Dict:
        """Simula DCA regular cada semana."""
        total_invested = 0
        total_coins = 0

        for _, row in df.iterrows():
            if pd.notna(row['close']):
                total_invested += self.base_investment
                coins_bought = self.base_investment / row['close']
                total_coins += coins_bought

        final_value = total_coins * df['close'].iloc[-1]
        total_return = (final_value - total_invested) / total_invested

        return {
            'total_invested': total_invested,
            'total_coins': total_coins,
            'final_value': final_value,
            'total_return': total_return,
            'purchases': len(df)
        }

    def simulate_conditional_dca(self, df: pd.DataFrame, condition: str, threshold: float, operator: str) -> Dict:
        """Simula DCA condicional basado en un indicador."""
        total_invested = 0
        total_coins = 0
        purchases = 0

        for _, row in df.iterrows():
            if pd.notna(row['close']) and pd.notna(row[condition]):
                # Evaluar condición
                if operator == '<' and row[condition] < threshold:
                    should_buy = True
                elif operator == '>' and row[condition] > threshold:
                    should_buy = True
                else:
                    should_buy = False

                if should_buy:
                    total_invested += self.base_investment
                    coins_bought = self.base_investment / row['close']
                    total_coins += coins_bought
                    purchases += 1

        if total_invested > 0:
            final_value = total_coins * df['close'].iloc[-1]
            total_return = (final_value - total_invested) / total_invested
        else:
            final_value = 0
            total_return = 0

        return {
            'total_invested': total_invested,
            'total_coins': total_coins,
            'final_value': final_value,
            'total_return': total_return,
            'purchases': purchases
        }

    def generate_backtest_report(self, symbol: str = None):
        """
        Genera un reporte completo de backtesting.
        """
        if symbol:
            self.symbol = symbol

        print("="*80)
        print(f"📊 BACKTEST HISTÓRICO DE TIMING DCA - {self.symbol}")
        print("="*80)

        # 1. Obtener datos históricos
        df = self.fetch_historical_data()

        # 2. Calcular indicadores
        df = self.calculate_technical_indicators(df)

        # 3. Analizar patrones temporales
        timing_patterns = self.analyze_timing_patterns(df)

        # 4. Analizar puntos de entrada técnicos
        technical_analysis = self.analyze_technical_entry_points(df)

        # 5. Simular estrategias DCA
        strategies = self.simulate_dca_strategies(df)

        # Generar reporte
        self.print_timing_report(timing_patterns)
        self.print_technical_report(technical_analysis)
        self.print_strategy_report(strategies)

        return {
            'data': df,
            'timing_patterns': timing_patterns,
            'technical_analysis': technical_analysis,
            'strategies': strategies
        }

    def print_timing_report(self, patterns: Dict):
        """Imprime el reporte de patrones temporales."""
        print("\n🗓️ ANÁLISIS DE PATRONES TEMPORALES")
        print("-" * 50)

        # Mejores meses
        monthly = patterns['monthly_patterns'].sort_values('forward_return_4w_mean', ascending=False)
        print("\n📅 MEJORES MESES PARA DCA (Return promedio 4 semanas):")
        for _, row in monthly.head(6).iterrows():
            month_names = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                          'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            print(f"   {month_names[int(row['month'])]}: {row['forward_return_4w_mean']:.3f} ({row['forward_return_4w_count']:.0f} muestras)")

        # Mejores trimestres
        quarterly = patterns['quarterly_patterns'].sort_values('forward_return_4w_mean', ascending=False)
        print(f"\n📊 MEJORES TRIMESTRES:")
        quarter_names = ['', 'Q1 (Ene-Mar)', 'Q2 (Abr-Jun)', 'Q3 (Jul-Sep)', 'Q4 (Oct-Dic)']
        for _, row in quarterly.iterrows():
            print(f"   {quarter_names[int(row['quarter'])]}: {row['forward_return_4w_mean']:.3f}")

        # Mejores semanas del año
        best_weeks = patterns['weekly_patterns']['best_weeks_4w']
        print(f"\n⭐ TOP 5 SEMANAS DEL AÑO PARA DCA:")
        for _, row in best_weeks.iterrows():
            print(f"   Semana {int(row['week_of_year'])}: {row['forward_return_4w_mean']:.3f} (RSI prom: {row['rsi_mean']:.1f})")

    def print_technical_report(self, analysis: Dict):
        """Imprime el reporte de análisis técnico."""
        print("\n🎯 ANÁLISIS DE PUNTOS DE ENTRADA TÉCNICOS")
        print("-" * 50)

        # RSI Analysis
        print("\n📈 ANÁLISIS POR RSI:")
        rsi_data = analysis['rsi_analysis'].sort_values('forward_return_4w_mean', ascending=False)
        for _, row in rsi_data.iterrows():
            print(f"   {row['rsi_range']}: {row['forward_return_4w_mean']:.3f} ({row['forward_return_4w_count']:.0f} casos)")

        # Bollinger Analysis
        print(f"\n📊 ANÁLISIS POR BOLLINGER %B:")
        bb_data = analysis['bb_analysis'].sort_values('forward_return_4w_mean', ascending=False)
        for _, row in bb_data.iterrows():
            print(f"   {row['bb_range']}: {row['forward_return_4w_mean']:.3f} ({row['forward_return_4w_count']:.0f} casos)")

        # Z-Score Analysis
        print(f"\n📉 ANÁLISIS POR Z-SCORE:")
        zscore_data = analysis['zscore_analysis'].sort_values('forward_return_4w_mean', ascending=False)
        for _, row in zscore_data.iterrows():
            print(f"   {row['zscore_range']}: {row['forward_return_4w_mean']:.3f} ({row['forward_return_4w_count']:.0f} casos)")

    def print_strategy_report(self, strategies: Dict):
        """Imprime el reporte de estrategias."""
        print("\n💰 COMPARACIÓN DE ESTRATEGIAS DCA")
        print("-" * 50)

        for strategy_name, results in strategies.items():
            name_map = {
                'regular_dca': 'DCA Regular (semanal)',
                'rsi_based_dca': 'DCA cuando RSI < 50',
                'zscore_based_dca': 'DCA cuando Z-Score < -0.5',
                'bollinger_based_dca': 'DCA cuando %B < 0.3'
            }

            display_name = name_map.get(strategy_name, strategy_name)
            print(f"\n🔹 {display_name}:")
            print(f"   💵 Invertido total: ${results['total_invested']:,.2f}")
            print(f"   🪙 Monedas acumuladas: {results['total_coins']:.6f}")
            print(f"   💎 Valor final: ${results['final_value']:,.2f}")
            print(f"   📈 Return total: {results['total_return']:.2%}")
            print(f"   🛒 Compras realizadas: {results['purchases']}")


def main():
    """Función principal para ejecutar el backtest."""
    # Crear instancia del backtester
    backtester = DCATimingBacktester("BTCUSDT")

    # Ejecutar análisis completo
    results = backtester.generate_backtest_report()

    print("\n" + "="*80)
    print("✅ BACKTEST COMPLETADO")
    print("="*80)


if __name__ == "__main__":
    main()
