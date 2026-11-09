import logging

logger = logging.getLogger(__name__)


def check_gate(result: dict) -> bool:
    """Run after each agent. True keeps the ticker, False drops it."""
    ticker = result.get("ticker", "UNKNOWN")

    if result.get("error"):
        logger.info(f"Gate dropped {ticker} - agent error: {result['error']}")
        return False

    if result.get("data_missing"):
        logger.info(f"Gate dropped {ticker} - missing data: {result.get('reason', '')}")
        return False

    if result.get("passed") is False:
        logger.info(f"Gate dropped {ticker} - {result.get('reason', 'no reason given')}")
        return False

    return True
