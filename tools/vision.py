"""
E.V. Vision — Screenshot capture and image analysis.
"""

import base64
import logging
from pathlib import Path
from datetime import datetime

import config

logger = logging.getLogger("ev.tools.vision")


def take_screenshot(target: str = "full_screen") -> str:
    """
    Take a screenshot and save it.
    Returns the path to the saved image.
    """
    try:
        import mss

        screenshot_dir = config.DATA_DIR / "screenshots"
        screenshot_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = screenshot_dir / filename

        with mss.mss() as sct:
            if target == "active_window":
                # Capture primary monitor (closest to active window on Windows)
                monitor = sct.monitors[1]
            else:
                # Full screen (all monitors combined)
                monitor = sct.monitors[0]

            screenshot = sct.grab(monitor)
            
            from PIL import Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.save(str(filepath))

        return f"Screenshot saved: {filepath}"

    except ImportError:
        return "Error: mss and/or Pillow not installed. Run: pip install mss Pillow"
    except Exception as e:
        return f"Error taking screenshot: {e}"


async def analyze_image(image_path: str, question: str = "") -> str:
    """
    Analyze an image using Vision-capable LLM (Gemini 2.0 Flash or OpenAI-compatible Vision API).
    """
    try:
        path = Path(image_path).resolve()
        if not path.exists():
            return f"Error: Image not found: {image_path}"

        # Read and encode image
        with open(path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Determine MIME type
        suffix = path.suffix.lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(suffix, "image/png")

        from openai import AsyncOpenAI

        # Prefer Gemini for Vision as it natively supports image understanding
        if config.GEMINI_API_KEY:
            api_key = config.GEMINI_API_KEY
            base_url = config.GEMINI_BASE_URL
            model = config.GEMINI_MODEL
        elif config.GROQ_API_KEY:
            api_key = config.GROQ_API_KEY
            base_url = config.GROQ_BASE_URL
            model = "llama-3.2-11b-vision-preview"
        else:
            api_key = config.DEEPSEEK_API_KEY
            base_url = config.DEEPSEEK_BASE_URL
            model = config.DEEPSEEK_MODEL

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=15.0,
        )

        prompt = question or "Describe this image in detail. If there is text, read it."

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1024,
        )

        return response.choices[0].message.content or "No analysis available."

    except Exception as e:
        logger.error(f"Error analyzing image: {e}")
        return f"Error analyzing image: {e}"
