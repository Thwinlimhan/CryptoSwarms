import httpx
import json
import logging
from typing import Any, Dict, List, Optional
from api.settings import settings

logger = logging.getLogger("llm_client")

class LLMClient:
    """Client for SGLang or OpenAI-compatible LLM providers."""
    
    def __init__(self, host: str = None, port: int = None, api_key: str = None):
        self.host = host or settings.sglang_host
        self.port = port or settings.sglang_port
        self.api_key = api_key or "sk-no-key-needed"
        self.base_url = f"http://{self.host}:{self.port}/v1"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: List[Dict[str, str]], model: str = "default", temperature: float = 0.7, json_response: bool = False) -> str:
        """Send a chat completion request."""
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_response:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = await self.client.post(url, json=payload, headers={"Authorization": f"Bearer {self.api_key}"})
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM Chat Error: {e}")
            raise

    async def complete(self, prompt: str, **kwargs) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self.chat(messages, **kwargs)

    async def close(self):
        await self.client.aclose()
