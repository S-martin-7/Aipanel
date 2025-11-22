"""
OCR processor for AIPanel.

Supports multiple OCR backends:
- Tesseract (local, free)
- Google Cloud Vision (cloud, paid)
- OpenAI Vision (using GPT-4 Vision)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
import base64
import io
from pathlib import Path

from PIL import Image
import httpx

from app.core.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OCRProvider(ABC):
    """Base class for OCR providers."""

    @abstractmethod
    async def extract_text(self, image_data: bytes, language: str = "spa") -> str:
        """Extract text from image bytes."""
        pass

    @abstractmethod
    async def extract_text_with_boxes(
        self, image_data: bytes, language: str = "spa"
    ) -> List[dict]:
        """Extract text with bounding boxes."""
        pass


class TesseractOCR(OCRProvider):
    """
    Tesseract OCR provider (local processing).

    Requires pytesseract and tesseract-ocr installed.
    """

    def __init__(self, tesseract_path: str = None):
        try:
            import pytesseract
            self.pytesseract = pytesseract
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
        except ImportError:
            logger.warning("pytesseract not installed. Tesseract OCR will not work.")
            self.pytesseract = None

    async def extract_text(self, image_data: bytes, language: str = "spa") -> str:
        """Extract text from image using Tesseract."""
        if not self.pytesseract:
            raise RuntimeError("pytesseract not available")

        image = Image.open(io.BytesIO(image_data))

        # Preprocess image for better OCR
        image = self._preprocess_image(image)

        # Map language codes
        lang_map = {"spa": "spa", "eng": "eng", "por": "por"}
        tesseract_lang = lang_map.get(language, "spa+eng")

        text = self.pytesseract.image_to_string(image, lang=tesseract_lang)
        return text.strip()

    async def extract_text_with_boxes(
        self, image_data: bytes, language: str = "spa"
    ) -> List[dict]:
        """Extract text with bounding boxes using Tesseract."""
        if not self.pytesseract:
            raise RuntimeError("pytesseract not available")

        image = Image.open(io.BytesIO(image_data))
        image = self._preprocess_image(image)

        lang_map = {"spa": "spa", "eng": "eng", "por": "por"}
        tesseract_lang = lang_map.get(language, "spa+eng")

        data = self.pytesseract.image_to_data(
            image, lang=tesseract_lang, output_type=self.pytesseract.Output.DICT
        )

        results = []
        for i, text in enumerate(data["text"]):
            if text.strip():
                results.append({
                    "text": text,
                    "confidence": data["conf"][i],
                    "box": {
                        "x": data["left"][i],
                        "y": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                    },
                })

        return results

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to grayscale
        if image.mode != "L":
            image = image.convert("L")

        # Resize if too small
        min_width = 1000
        if image.width < min_width:
            ratio = min_width / image.width
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        return image


class OpenAIVisionOCR(OCRProvider):
    """
    OCR using OpenAI GPT-4 Vision.

    More accurate for complex documents but costs more.
    """

    def __init__(self, api_key: str = None):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key or settings.OPENAI_API_KEY)

    async def extract_text(self, image_data: bytes, language: str = "spa") -> str:
        """Extract text from image using GPT-4 Vision."""
        base64_image = base64.b64encode(image_data).decode("utf-8")

        # Detect image type
        image = Image.open(io.BytesIO(image_data))
        format_map = {"JPEG": "jpeg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}
        image_format = format_map.get(image.format, "jpeg")

        lang_name = {"spa": "Spanish", "eng": "English", "por": "Portuguese"}.get(language, "Spanish")

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Extract ALL text from this image.
                            The text is primarily in {lang_name}.
                            Return ONLY the extracted text, preserving the original layout and formatting as much as possible.
                            If there are tables, format them clearly.
                            If there are multiple columns, process them in reading order.
                            Do not add any explanations or comments.""",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )

        return response.choices[0].message.content.strip()

    async def extract_text_with_boxes(
        self, image_data: bytes, language: str = "spa"
    ) -> List[dict]:
        """
        Extract text with approximate positions using GPT-4 Vision.

        Note: GPT-4 Vision doesn't provide exact bounding boxes,
        so this returns structured text regions.
        """
        base64_image = base64.b64encode(image_data).decode("utf-8")

        image = Image.open(io.BytesIO(image_data))
        format_map = {"JPEG": "jpeg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}
        image_format = format_map.get(image.format, "jpeg")

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract text from this image and identify different regions.
                            Return a JSON array where each item has:
                            - "text": the extracted text
                            - "type": "heading", "paragraph", "table", "list", "caption", etc.
                            - "position": "top", "middle", "bottom", "left", "right", etc.

                            Return ONLY the JSON array, no other text.""",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{image_format};base64,{base64_image}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            max_tokens=4096,
        )

        import json
        try:
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        except json.JSONDecodeError:
            return [{"text": response.choices[0].message.content, "type": "unknown"}]


class OCRService:
    """
    High-level OCR service that manages different providers.
    """

    def __init__(self):
        self.tesseract = TesseractOCR()
        self.openai_vision = None  # Lazy initialization

    def _get_openai_vision(self) -> OpenAIVisionOCR:
        """Get OpenAI Vision provider (lazy init)."""
        if self.openai_vision is None:
            self.openai_vision = OpenAIVisionOCR()
        return self.openai_vision

    async def extract_text(
        self,
        image_data: bytes,
        language: str = "spa",
        provider: str = "auto",
        high_quality: bool = False,
    ) -> dict:
        """
        Extract text from image.

        Args:
            image_data: Image bytes
            language: Language code (spa, eng, por)
            provider: "tesseract", "openai", or "auto"
            high_quality: Use high-quality (but more expensive) extraction

        Returns:
            Dict with extracted text and metadata
        """
        if provider == "auto":
            # Use OpenAI for high quality, Tesseract otherwise
            provider = "openai" if high_quality else "tesseract"

        try:
            if provider == "tesseract":
                text = await self.tesseract.extract_text(image_data, language)
                provider_used = "tesseract"
            else:
                text = await self._get_openai_vision().extract_text(image_data, language)
                provider_used = "openai_vision"

            # Get image info
            image = Image.open(io.BytesIO(image_data))

            return {
                "success": True,
                "text": text,
                "provider": provider_used,
                "language": language,
                "image_info": {
                    "width": image.width,
                    "height": image.height,
                    "format": image.format,
                },
                "char_count": len(text),
                "word_count": len(text.split()),
            }
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": provider,
            }

    async def extract_from_file(
        self,
        file_path: str,
        language: str = "spa",
        provider: str = "auto",
    ) -> dict:
        """Extract text from image file."""
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": "File not found"}

        with open(path, "rb") as f:
            image_data = f.read()

        return await self.extract_text(image_data, language, provider)

    async def batch_extract(
        self,
        images: List[bytes],
        language: str = "spa",
        provider: str = "tesseract",
    ) -> List[dict]:
        """Extract text from multiple images."""
        results = []
        for image_data in images:
            result = await self.extract_text(image_data, language, provider)
            results.append(result)
        return results

    def supported_formats(self) -> List[str]:
        """Return list of supported image formats."""
        return ["png", "jpg", "jpeg", "gif", "webp", "bmp", "tiff"]


# Global service instance
ocr_service = OCRService()
