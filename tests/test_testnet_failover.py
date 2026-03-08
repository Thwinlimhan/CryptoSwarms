import pytest

from agents.execution.execution_agent import ExchangeExecutionError, OrderRequest
from agents.execution.testnet_failover import ExchangeFailoverExecutor


class FlakyAdapter:
    def __init__(self, name: str, fail_times: int):
        self.name = name
        self._remaining = fail_times

    def place_order(self, order: OrderRequest):
        if self._remaining > 0:
            self._remaining -= 1
            raise RuntimeError("temporary failure")
        return {"exchange": self.name, "status": "accepted"}


def test_failover_executor_retries_then_succeeds():
    adapter = FlakyAdapter("binance_testnet", fail_times=2)
    executor = ExchangeFailoverExecutor([adapter], max_attempts_per_adapter=3)

    result = executor.execute(OrderRequest(symbol="BTCUSDT", side="buy", quantity=0.1, stop_loss=59000, take_profit=62000))

    assert result["exchange"] == "binance_testnet"
    assert result["attempt"] == 3


def test_failover_executor_moves_to_next_adapter():
    a1 = FlakyAdapter("binance_testnet", fail_times=5)
    a2 = FlakyAdapter("hyperliquid_testnet", fail_times=0)
    executor = ExchangeFailoverExecutor([a1, a2], max_attempts_per_adapter=2)

    result = executor.execute(OrderRequest(symbol="BTCUSDT", side="buy", quantity=0.1, stop_loss=59000, take_profit=62000))
    assert result["exchange"] == "hyperliquid_testnet"


def test_failover_executor_raises_when_all_fail():
    a1 = FlakyAdapter("binance_testnet", fail_times=5)
    executor = ExchangeFailoverExecutor([a1], max_attempts_per_adapter=2)

    with pytest.raises(ExchangeExecutionError):
        executor.execute(OrderRequest(symbol="BTCUSDT", side="buy", quantity=0.1, stop_loss=59000, take_profit=62000))

