# -*- coding: utf-8 -*-
"""Compatibility exports for StockSight HTML report sections."""

from .html_utils import (
    HEADER_GRADIENTS,
    LEVEL_COLORS,
    TYPE_COLORS,
    VERSION,
    _calculate_risk_score,
    _get_risk_status,
    _html,
    _level_pie_gradient,
    _metric_card,
    _metric_card_heat,
    _pie_gradient,
    _target_stock_and_signals,
)
from .html_charts import (
    _decision_card_html,
    _nav_html,
    _radar_html,
    _risk_distribution_html,
    _risk_gauge_html,
    _signal_composition_html,
)
from .html_panels import (
    _news_html,
    _price_range_html,
    _quality_html,
    _risk_notes_html,
    _stock_table_html,
    _volume_price_html,
)

__all__ = [
    "HEADER_GRADIENTS",
    "LEVEL_COLORS",
    "TYPE_COLORS",
    "VERSION",
    "_calculate_risk_score",
    "_decision_card_html",
    "_get_risk_status",
    "_html",
    "_level_pie_gradient",
    "_metric_card",
    "_metric_card_heat",
    "_nav_html",
    "_news_html",
    "_pie_gradient",
    "_price_range_html",
    "_quality_html",
    "_radar_html",
    "_risk_distribution_html",
    "_risk_gauge_html",
    "_risk_notes_html",
    "_signal_composition_html",
    "_stock_table_html",
    "_target_stock_and_signals",
    "_volume_price_html",
]
