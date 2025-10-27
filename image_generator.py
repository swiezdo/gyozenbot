import logging
from openai import OpenAI
from config import OPENAI_API_KEY, IMAGE_MODEL, IMAGE_SIZE

client = OpenAI(api_key=OPENAI_API_KEY)

async def generate_image(prompt: str) -> str | None:
    try:
        resp = client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=IMAGE_SIZE,
            n=1,
        )
        return resp.data[0].url
    except Exception as e:
        logging.error(f"Image generation error: {e}")
        return None
