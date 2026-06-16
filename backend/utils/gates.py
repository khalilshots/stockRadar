import logging

logger = logging.getLogger(__name__)

def check_gate(result: dict) -> bool:
    """
    Runs after every agent.
    Returns True  → ticker passes, move forward
    Returns False → ticker dropped, stop processing it
    """

    # Did the agent report an error?
    if result.get("error"):
        logger.warning(
            f"Gate dropped {result.get('ticker', 'UNKNOWN')} "
            f"→ agent error: {result['error']}"
        )
        return False

    # Did the agent say it was missing data?
    if result.get("data_missing"):
        logger.warning(
            f"Gate dropped {result.get('ticker', 'UNKNOWN')} "
            f"→ insufficient data"
        )
        return False

    # Did the agent explicitly say this ticker failed?
    if result.get("passed") == False:
        logger.warning(
            f"Gate dropped {result.get('ticker', 'UNKNOWN')} "
            f"→ {result.get('reason', 'no reason given')}"
        )
        return False

    # Everything looks clean — ticker moves forward
    return True