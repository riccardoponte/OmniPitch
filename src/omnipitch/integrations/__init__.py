"""
Enterprise integrations for OmniPitch: Power Automate, Azure Logic Apps & Microsoft Teams.
"""

from .power_automate import (
    PowerAutomateDispatcher,
    build_goal_adaptive_card,
    build_tactical_shift_adaptive_card,
    build_incident_adaptive_card,
)

__all__ = [
    "PowerAutomateDispatcher",
    "build_goal_adaptive_card",
    "build_tactical_shift_adaptive_card",
    "build_incident_adaptive_card",
]
