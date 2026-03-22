import config
from datetime import date
from logger import logger


class RiskManager:

    def __init__(self):
        self.trades_today    = 0
        self.last_reset_date = date.today()

    def _reset_if_new_day(self):
        today = date.today()
        if today != self.last_reset_date:
            logger.info(f"RiskManager: new day {today}, resetting trade counter.")
            self.trades_today    = 0
            self.last_reset_date = today

    def allow_trade(self) -> bool:
        self._reset_if_new_day()
        if self.trades_today >= config.MAX_TRADES_PER_DAY:
            logger.warning(
                f"RiskManager: daily trade limit {config.MAX_TRADES_PER_DAY} reached."
            )
            return False
        self.trades_today += 1
        return True