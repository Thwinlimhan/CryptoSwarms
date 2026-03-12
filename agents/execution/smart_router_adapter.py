import logging
from typing import Any

from cryptoswarms.execution_router import OrderExecutor, OrderIntent

logger = logging.getLogger(__name__)


class HyperliquidMcpExecutor(OrderExecutor):
    """
    A concrete OrderExecutor that acts as a bridge to the Hyperliquid MCP server.
    
    This executor assumes the MCP server handles wallet signing, nonce management,
    and payload construction via standard MCP JSON-RPC messages.
    """

    def __init__(self, mcp_client: Any) -> None:
        """
        :param mcp_client: An instantiated client capable of sending tool execution
                           requests to the hyperliquid-mcp server.
        """
        self.mcp_client = mcp_client

    def execute(self, intent: OrderIntent, reduce_only: bool = False) -> None:
        """
        Sends an order instruction to the Hyperliquid MCP Server.
        
        Note: In a true async stack this should be async, but we adhere to the existing
        `OrderExecutor` protocol which is synchronous. Real-world implementations might
        need to wrap this with an asyncio loop if the MCP client is async.
        """
        tool_payload = {
            "name": "place_order",
            "parameters": {
                "coin": intent.symbol.replace("USDT", ""),  # HL uses standard names like BTC
                "is_buy": intent.side.upper() == "BUY",
                "sz": intent.quantity,
                "reduce_only": reduce_only or intent.reduce_only,
            }
        }

        try:
            # Assuming `mcp_client.call_tool` executes the request synchronously or is 
            # wrapped to block until completion.
            response = self.mcp_client.call_tool("place_order", tool_payload["parameters"])
            logger.info(f"Execution routed to Hyperliquid MCP: {response}")
        except Exception as e:
            logger.error(f"Failed to route order to Hyperliquid MCP: {e}")
            raise RuntimeError(f"Order failed at broker level: {e}") from e
