"""Group-level academic-risk profiles and cautious suggestions (Phase 6)."""

from analytics.risk.profiles import PROFILE_PAIRS, PROFILE_VARIABLES, risk_profiles
from analytics.risk.suggestions import DISCLAIMER, RULES, suggest

__all__ = ["DISCLAIMER", "PROFILE_PAIRS", "PROFILE_VARIABLES", "RULES", "risk_profiles", "suggest"]
