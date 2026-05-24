import os
import json
import httpx
import sys
from typing import Optional
from rich.console import Console
from .config import settings

console = Console(stderr=True)

def safe_char(char: str, fallback: str) -> str:
    try:
        char.encode(sys.stdout.encoding or "ascii")
        return char
    except Exception:
        return fallback

WARN = safe_char("⚠️", "!")
CROSS = safe_char("❌", "x")

def get_ai_credentials():
    api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY") or settings.ai_api_key
    base_url = os.getenv("AI_BASE_URL") or os.getenv("OPENAI_BASE_URL") or settings.ai_base_url
    model = os.getenv("AI_MODEL") or os.getenv("OPENAI_MODEL") or settings.ai_model
    return api_key, base_url, model

def query_llm(
    system_prompt: str,
    user_prompt: Optional[str] = None,
    json_format: bool = False,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """Queries the OpenAI-compatible REST endpoint using httpx synchronously with a 5-second timeout."""
    api_key, base_url, model = get_ai_credentials()
    
    if not api_key:
        console.print(f"[yellow]{WARN} Warning: AI API key not configured. Set AI_API_KEY in environment or ~/.task-cli.toml.[/yellow]")
        raise RuntimeError("AI API key not configured.")
        
    base_url_cleaned = base_url.rstrip('/')
    if base_url_cleaned.endswith("/chat/completions"):
        base_url_cleaned = base_url_cleaned[:-17].rstrip('/')
    url = f"{base_url_cleaned}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "system", "content": system_prompt}]
    if user_prompt:
        messages.append({"role": "user", "content": user_prompt})
        
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens if max_tokens is not None else 4096
    }
    
    if temperature is not None:
        payload["temperature"] = temperature
        
    if json_format:
        payload["response_format"] = {"type": "json_object"}
        
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=5.0)
        
        if response.status_code != 200:
            console.print(f"[red]{CROSS} LLM API Error: Status {response.status_code}[/red]")
            console.print(f"[red]Response Content: {response.text}[/red]")
            raise RuntimeError(f"API returned status {response.status_code}")
            
        data = response.json()
        return data["choices"][0]["message"]["content"]
        
    except httpx.TimeoutException:
        console.print(f"[red]{CROSS} AI Call Timed Out (5s limit exceeded).[/red]")
        raise
    except Exception as e:
        console.print(f"[red]{CROSS} AI Call Failed: {e}[/red]")
        raise
