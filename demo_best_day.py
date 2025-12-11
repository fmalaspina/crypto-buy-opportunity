"""
Ejemplo de uso del análisis de mejor día de la semana para DCA
"""

from crypto_buy_opportunity import QuantitativeAnalyst

def demo_best_day_analysis():
    """
    Demuestra cómo usar el análisis del mejor día de la semana.
    """

    print("="*80)
    print("🎯 DEMO: ANÁLISIS DEL MEJOR DÍA PARA DCA")
    print("="*80)

    # Crear analista para BTC
    analyst = QuantitativeAnalyst(base_investment=250.0, symbol="BTCUSDT")

    # Obtener información detallada de timing
    timing_info = analyst.get_enhanced_timing_info()

    print(f"\n📊 INFORMACIÓN DETALLADA DEL MEJOR DÍA:")
    print(f"   🏆 Mejor día histórico: {timing_info['best_day']}")
    print(f"   📈 Score: {timing_info['best_day_score']:.4f}")
    print(f"   🔬 Confianza: {timing_info['best_day_confidence']}")
    print(f"   📅 Día actual: {timing_info['current_weekday']}")
    print(f"   🎯 ¿Es hoy el mejor día?: {'SÍ' if timing_info['is_best_day_today'] else 'NO'}")

    if timing_info['weekday_analysis']:
        print(f"\n📈 ANÁLISIS COMPLETO POR DÍA DE SEMANA:")
        print(f"{'Día':<12} {'Return %':<10} {'Éxito %':<10} {'Score':<10} {'Días':<8}")
        print("-" * 50)

        # Ordenar por score
        sorted_days = sorted(timing_info['weekday_analysis'].items(),
                           key=lambda x: x[1]['combined_score'], reverse=True)

        for day, stats in sorted_days:
            return_pct = stats['avg_forward_return'] * 100
            success_rate = stats['positive_rate'] * 100
            score = stats['combined_score']
            count = stats['count']

            # Emoji para el mejor día
            emoji = "🏆" if day == timing_info['best_day'] else "  "

            print(f"{emoji}{day:<12} {return_pct:+6.2f}    {success_rate:6.0f}    {score:+7.4f}  {count:>6}")

    print(f"\n💰 RECOMENDACIONES:")
    if timing_info['is_best_day_today']:
        print(f"   🟢 ¡EJECUTAR DCA HOY! Es {timing_info['best_day']}")
    elif timing_info['best_day_urgency'] == 'INMEDIATA':
        print(f"   🟡 Preparar DCA - {timing_info['best_day']} en {timing_info['hours_until_best_day']:.1f}h")
    elif timing_info['best_day_urgency'] == 'ALTA':
        print(f"   🔵 Planificar DCA - {timing_info['best_day']} es mañana")
    else:
        print(f"   ⏳ Esperar - {timing_info['best_day']} en {timing_info['hours_until_best_day']:.0f}h")

    # Análisis comparativo
    print(f"\n🔍 FLEXIBILIDAD DEL ANÁLISIS:")
    print(f"   ✅ Puedes ejecutar el análisis cualquier día de la semana")
    print(f"   📊 El sistema identifica automáticamente el mejor día histórico")
    print(f"   🎯 Las recomendaciones se ajustan según el día actual vs el mejor día")
    print(f"   📈 No hay dependencia fija en ningún día específico")

if __name__ == "__main__":
    demo_best_day_analysis()
