from analytics.aggregates import daily_summary

from .corpus import comparativa as calcular_comparativa
from .models import Insight
from .prompt import build_prompt


def generate_for_business(business, day, llm):
    """Genera (o regenera) el insight de un día. Devuelve None si no hubo datos."""
    summary = daily_summary(business, day)
    if summary["total_visitors"] == 0 and not summary["hourly"]:
        return None

    comp = calcular_comparativa(business, day)
    body = llm.generate(build_prompt(summary, business, comparativa=comp))
    insight, _ = Insight.objects.update_or_create(
        business=business, day=day, defaults={"body": body, "model": llm.model}
    )
    return insight
