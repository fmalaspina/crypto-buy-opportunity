import pandas as pd
import matplotlib.pyplot as plt
from thursday_dca_backtest import ThursdayDCABacktester
from datetime import datetime

class DCAComparisonAnalyzer:
    """
    Analizador avanzado que compara múltiples estrategias DCA.
    """

    def __init__(self, symbol: str = "BTCUSDT", start_date: str = "2020-01-01", base_investment: float = 250.0):
        self.symbol = symbol
        self.start_date = start_date
        self.base_investment = base_investment

    def run_comprehensive_analysis(self):
        """
        Ejecuta un análisis comparativo completo entre diferentes estrategias.
        """
        print("="*80)
        print("📊 ANÁLISIS COMPARATIVO COMPLETO DE ESTRATEGIAS DCA")
        print("="*80)

        # 1. Estrategia: Jueves con Análisis Cuantitativo
        print("\n🤖 1. EJECUTANDO: DCA Jueves con Análisis Cuantitativo...")
        thursday_backtester = ThursdayDCABacktester(self.symbol, self.start_date, self.base_investment)
        thursday_results = thursday_backtester.run_thursday_backtest()

        # 2. Comparar con diferentes días de la semana
        print("\n📅 2. COMPARANDO CON OTROS DÍAS DE LA SEMANA...")
        day_results = self.compare_different_weekdays()

        # 3. Generar reporte comparativo
        self.generate_comparison_report(thursday_results, day_results)

    def compare_different_weekdays(self):
        """
        Compara el rendimiento de DCA en diferentes días de la semana.
        """
        weekdays = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday",
            3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"
        }

        results = {}

        # Obtener datos históricos
        backtester = ThursdayDCABacktester(self.symbol, self.start_date, self.base_investment)
        df = backtester.fetch_daily_data(self.start_date)

        for weekday_num, weekday_name in weekdays.items():
            print(f"   Analizando {weekday_name}...")

            # Filtrar días específicos
            weekday_data = df[df["weekday"] == weekday_num].copy()

            if len(weekday_data) == 0:
                continue

            # Simular DCA regular en ese día
            total_invested = 0
            total_coins = 0

            for _, row in weekday_data.iterrows():
                total_invested += self.base_investment
                coins_bought = self.base_investment / row["close"]
                total_coins += coins_bought

            final_value = total_coins * df["close"].iloc[-1]
            total_return = (final_value - total_invested) / total_invested if total_invested > 0 else 0

            results[weekday_name] = {
                "total_invested": total_invested,
                "total_coins": total_coins,
                "final_value": final_value,
                "total_return": total_return,
                "operations": len(weekday_data)
            }

        return results

    def generate_comparison_report(self, thursday_results, day_results):
        """
        Genera un reporte comparativo detallado.
        """
        print("\n" + "="*80)
        print("📈 REPORTE COMPARATIVO DE ESTRATEGIAS DCA")
        print("="*80)

        # Resultado de Thursday con análisis cuantitativo
        thursday_return = thursday_results["total_return"]
        thursday_invested = thursday_results["total_invested"]
        thursday_value = thursday_results["final_value"]

        print(f"\n🤖 JUEVES CON ANÁLISIS CUANTITATIVO:")
        print(f"   💵 Invertido: ${thursday_invested:,.2f}")
        print(f"   💎 Valor final: ${thursday_value:,.2f}")
        print(f"   📈 Return: {thursday_return:.2%}")
        print(f"   🛒 Operaciones: {thursday_results['trades_count']}")

        print(f"\n📅 COMPARACIÓN POR DÍA DE LA SEMANA (DCA Regular):")
        print(f"{'Día':<12} {'Return %':<12} {'Valor Final':<15} {'Operaciones':<12}")
        print("-" * 55)

        # Ordenar por return
        sorted_days = sorted(day_results.items(), key=lambda x: x[1]["total_return"], reverse=True)

        best_day_regular = None
        best_return_regular = -999

        for day, results in sorted_days:
            return_pct = results["total_return"] * 100
            value = results["final_value"]
            ops = results["operations"]

            if results["total_return"] > best_return_regular:
                best_day_regular = day
                best_return_regular = results["total_return"]

            emoji = "🏆" if day == "Thursday" else "  "
            print(f"{emoji}{day:<12} {return_pct:+8.2f}%    ${value:>12,.0f}  {ops:>10}")

        # Comparaciones específicas
        if "Thursday" in day_results:
            thursday_regular = day_results["Thursday"]
            print(f"\n🔍 COMPARACIONES ESPECÍFICAS:")
            print(f"\n📊 Thursday Regular DCA vs Thursday con Análisis:")
            print(f"   Regular Thursday: {thursday_regular['total_return']:.2%}")
            print(f"   Thursday + Análisis: {thursday_return:.2%}")
            improvement_vs_regular_thursday = ((thursday_return - thursday_regular['total_return']) / abs(thursday_regular['total_return'])) * 100
            print(f"   Mejora del análisis: {improvement_vs_regular_thursday:+.2f}%")

        # Comparar con el mejor día regular
        print(f"\n🥇 Mejor día regular: {best_day_regular} ({best_return_regular:.2%})")
        print(f"🤖 Thursday + Análisis: {thursday_return:.2%}")
        improvement_vs_best = ((thursday_return - best_return_regular) / abs(best_return_regular)) * 100
        print(f"📈 Thursday + Análisis vs Mejor día regular: {improvement_vs_best:+.2f}%")

        # Análisis de eficiencia de capital
        print(f"\n💰 ANÁLISIS DE EFICIENCIA DE CAPITAL:")
        avg_investment_regular = self.base_investment
        avg_investment_analyzed = thursday_invested / thursday_results['trades_count']
        capital_efficiency = ((thursday_return / (avg_investment_analyzed / avg_investment_regular)) / thursday_regular['total_return']) - 1

        print(f"   Inversión promedio regular: ${avg_investment_regular:.2f}")
        print(f"   Inversión promedio analizada: ${avg_investment_analyzed:.2f}")
        print(f"   Factor de capital: {avg_investment_analyzed/avg_investment_regular:.2f}x")

        # Resumen ejecutivo
        print(f"\n" + "="*50)
        print("📋 RESUMEN EJECUTIVO")
        print("="*50)

        if thursday_return > best_return_regular:
            print("✅ RESULTADO: Thursday + Análisis SUPERA al mejor DCA regular")
        else:
            print("❌ RESULTADO: Thursday + Análisis no supera al mejor DCA regular")

        print(f"🏆 Mejor estrategia identificada: ", end="")
        if thursday_return > best_return_regular:
            print("Thursday con Análisis Cuantitativo")
        else:
            print(f"{best_day_regular} DCA Regular")

        # Recomendación final
        print(f"\n💡 RECOMENDACIÓN:")
        if abs(improvement_vs_best) < 5:  # Diferencia menor al 5%
            print("   Las diferencias son menores. Usar Thursday + Análisis por:")
            print("   • Mayor flexibilidad en el monto de inversión")
            print("   • Capacidad de ajustarse a condiciones de mercado")
            print("   • Potencial de mejor timing en oportunidades extremas")
        elif improvement_vs_best > 0:
            print("   ✅ USAR Thursday + Análisis Cuantitativo")
            print(f"   📈 Mejora significativa de {improvement_vs_best:+.1f}%")
        else:
            print(f"   ⚠️ Considerar DCA regular en {best_day_regular}")
            print(f"   📊 Mejor rendimiento histórico: {improvement_vs_best:+.1f}%")

def main():
    """Función principal para análisis comparativo completo."""
    analyzer = DCAComparisonAnalyzer(
        symbol="BTCUSDT",
        start_date="2020-01-01",
        base_investment=250.0
    )

    analyzer.run_comprehensive_analysis()

if __name__ == "__main__":
    main()
