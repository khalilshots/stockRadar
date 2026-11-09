import logging

logger = logging.getLogger(__name__)

def check_gate(result: dict) -> bool:
    """Run after each agent. True keeps the ticker, False drops it."""

    if result.get("error"):
        logger.warning(
            f"Gate dropped {result.get('ticker', 'UNKNOWN')} "
            f"- agent error: {result['error']}"
        )
        return False

    if result.get("data_missing"):
        logger.warning(
            f"Gate dropped {result.get('ticker', 'UNKNOWN')} "
            f"- insufficient data"
        )
        return False

    if result.get("passed") == False:
        logger.warning(
            f"Gate dropped {result.get('ticker', 'UNKNOWN')} "
            f"- {result.get('reason', 'no reason given')}"
        )
        return False

    return True