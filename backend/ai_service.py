"""
Обёртка над OpenRouter API.
Работает с бесплатными моделями. Если одна модель перегружена (429)
или недоступна — автоматически пробует следующую из списка.
"""
import os
from dotenv import load_dotenv
import httpx

# Доверяем системным сертификатам Windows (обход VPN/антивирусной подмены)
try:
    import truststore
    truststore.inject_into_ssl()
    print(">> SSL: используем системные сертификаты")
except ImportError:
    print(">> SSL: truststore не установлен, используем стандартные")

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Основная модель (из .env) и запасные.
# openrouter/free — роутер OpenRouter: сам выбирает любую доступную бесплатную модель.
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "OPENROUTER_FALLBACKS",
        "openrouter/free,"
        "qwen/qwen3-next-80b-a3b-instruct:free,"
        "nvidia/nemotron-3-nano-30b-a3b:free",
    ).split(",")
    if m.strip()
]

# Порядок попыток: основная, затем запасные (без повторов)
MODELS_TO_TRY = list(dict.fromkeys([MODEL] + FALLBACK_MODELS))

# При этих статусах имеет смысл попробовать другую модель
RETRY_STATUSES = {403, 404, 408, 429, 500, 502, 503, 504}


async def ask_ai(messages: list[dict], temperature: float = 0.7, max_tokens: int = 1000) -> str:
    """
    Отправить запрос к ИИ.
    messages — список в формате OpenAI: [{"role": "user", "content": "..."}]
    Возвращает текст ответа.
    """
    if not API_KEY:
        raise ValueError("OPENROUTER_API_KEY не задан в .env")

    url = f"{BASE_URL}/chat/completions"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "EGE-Tutor",
    }

    last_error = "нет моделей для запроса"

    async with httpx.AsyncClient(timeout=90.0) as client:
        for model in MODELS_TO_TRY:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.HTTPError as e:
                last_error = f"{model}: сетевая ошибка {e}"
                print(f">> ИИ: {last_error}")
                continue

            if response.status_code == 200:
                data = response.json()
                try:
                    text = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    last_error = f"{model}: неожиданный ответ {str(data)[:200]}"
                    print(f">> ИИ: {last_error}")
                    continue
                if text and text.strip():
                    print(f">> ИИ: ответила модель {model}")
                    return text
                last_error = f"{model}: пустой ответ"
                continue

            last_error = f"{model}: HTTP {response.status_code}: {response.text[:300]}"
            print(f">> ИИ: {last_error}")
            if response.status_code not in RETRY_STATUSES:
                break   # 400/401 и т.п. — смена модели не поможет

    raise RuntimeError(f"Все модели недоступны. Последняя ошибка — {last_error}")


async def ask_ai_simple(prompt: str, system: str | None = None) -> str:
    """Упрощённый запрос: одна строка промпта."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return await ask_ai(messages)