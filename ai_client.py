import logging
from openai import OpenAI
from dialogue_styles import gyozen_style
from config import (
    AI_PROVIDER, DEEPSEEK_API_KEY, OPENAI_API_KEY,
    TEMPERATURE, MAX_TOKENS, FINE_TUNED_MODEL
)

# Выбор провайдера/модели
if AI_PROVIDER == "deepseek":
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    model_name = "deepseek-reasoner"
elif AI_PROVIDER == "openai":
    client = OpenAI(api_key=OPENAI_API_KEY)
    model_name = FINE_TUNED_MODEL if FINE_TUNED_MODEL else "gpt-4o"
else:
    raise ValueError("AI_PROVIDER должен быть 'openai' или 'deepseek'.")

async def get_response(prompt: str) -> str:
    try:
        # Если есть кастомная Fine-Tune — без system-промпта
        if AI_PROVIDER == "openai" and FINE_TUNED_MODEL:
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = [
                {"role": "system", "content": gyozen_style},
                {"role": "user", "content": prompt},
            ]

        resp = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logging.error(f"AI error ({AI_PROVIDER}): {e}")
        return "Извини, духи сегодня молчат. Попробуй ещё раз позже."
