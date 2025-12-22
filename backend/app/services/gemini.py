import base64
import io
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageFilter, ImageEnhance

from app.config import get_settings


# Directory for logging images
IMAGE_LOG_DIR = Path(__file__).parent.parent.parent / "image_logs"
IMAGE_LOG_DIR.mkdir(exist_ok=True)


@dataclass
class ImageResult:
    """Result from image processing with metadata."""
    image_base64: str
    prompt_used: str
    model_used: str


class GeminiService:
    _instance: Optional["GeminiService"] = None
    _initialized: bool = False
    _current_session: Optional[str] = None

    # Model names
    CONTENT_MODEL = "nano-banana-pro-preview"  # Supports image input/output
    IMAGE_GEN_MODEL = "imagen-3.0-generate-002"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self):
        """Lazy initialization to avoid import errors during testing."""
        if self._initialized:
            return

        try:
            from google import genai

            settings = get_settings()
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self._initialized = True
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini client: {e}")

    def _start_session(self) -> str:
        """Start a new image processing session with a unique ID."""
        self._current_session = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return self._current_session

    def _log_image(self, image: Image.Image, step: int, name: str) -> None:
        """Save an image to the log directory with session prefix."""
        if self._current_session is None:
            self._start_session()

        filename = f"{self._current_session}_{step:02d}_{name}.png"
        filepath = IMAGE_LOG_DIR / filename
        image.save(filepath, format="PNG")
        print(f"[Image Log] Saved: {filepath}")

    def _decode_image(self, base64_image: str) -> Image.Image:
        """Decode base64 image to PIL Image."""
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]
        image_data = base64.b64decode(base64_image)
        return Image.open(io.BytesIO(image_data))

    def _encode_image(self, image: Image.Image, format: str = "PNG") -> str:
        """Encode PIL Image to base64."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _pil_to_bytes(self, image: Image.Image, format: str = "PNG") -> bytes:
        """Convert PIL Image to bytes."""
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        return buffer.getvalue()

    def _get_extract_subject_prompt(self) -> str:
        """Get the prompt for subject extraction."""
        return """Extract and enhance the main subject from this image for use as a candle mold design.

CRITICAL REQUIREMENTS:
1. OUTPUT RESOLUTION: Generate a HIGH RESOLUTION image (4K). This is essential.
2. SUBJECT ISOLATION: Cleanly extract the primary subject/object with crisp, well-defined edges
3. BACKGROUND: Use a pure white or transparent background
4. ENHANCEMENT:
   - Enhance surface details and textures
   - Ensure smooth, clean edges suitable for mold making
   - Add subtle depth cues through shading
5. OPTIMIZATION FOR MOLDS:
   - Simplify overly complex or thin details that won't translate to a physical mold
   - Ensure the subject has good 3D depth variation
   - Smooth out noise or artifacts
   - Ideally with an orthogonal view rather than perspective
   - No perspective, i.e., the image should look like it's from an orthogonal view without perspective distortion

Output a clean, high-resolution, high-contrast image of the extracted subject."""

    def _get_generate_image_prompt(self, user_prompt: str) -> str:
        """Get the prompt for image generation optimized for candle mold creation.

        This prompt combines requirements from both image generation and subject extraction,
        so the generated image is already optimized for depth map creation without needing
        a separate extraction step.
        """
        return f"""Create a HIGH RESOLUTION (4K) image of the following subject, optimized for creating a decorative candle mold:

Subject: {user_prompt}

CRITICAL REQUIREMENTS:

1. IMAGE QUALITY:
   - High resolution (4K) with crisp, clear details
   - Professional quality with NO noise or artifacts
   - High contrast with well-defined edges

2. COMPOSITION:
   - Center the subject in the frame
   - Pure white or very light, clean background
   - Use an ORTHOGONAL view (no perspective distortion) - as if photographed straight-on
   - NO shadows, NO dramatic lighting - use flat, even illumination

3. SUBJECT OPTIMIZATION FOR MOLD MAKING:
   - Smooth surfaces that will release cleanly from a silicone mold
   - Simplify overly complex or thin details that won't translate to a physical mold
   - Ensure good 3D depth variation - the subject should have clear foreground/background separation
   - Enhance surface textures and details that will look good as a relief
   - Crisp, well-defined edges around the subject

4. WHAT TO AVOID:
   - DO NOT generate an image of a mold - generate the subject itself
   - NO thin or delicate details that won't work in wax
   - NO perspective distortion
   - NO shadows or complex lighting
   - NO busy or textured backgrounds

The image will be used to derive a depth map for 3D mold generation."""

    def _get_depth_map_prompt(self) -> str:
        """Get the prompt for depth map generation."""
        return """Generate a PROFESSIONAL QUALITY depth map from this image for 3D relief/mold creation.

CRITICAL REQUIREMENTS:
1. OUTPUT: High resolution grayscale depth map (4K)
2. DEPTH ENCODING:
   - Pure WHITE (255) = closest/highest points (front of relief, protruding areas)
   - Pure BLACK (0) = furthest/lowest points (back/base of the mold)
   - Smooth, continuous gradients between depth levels
3. QUALITY:
   - NO NOISE - the depth map must be smooth and clean
   - NO ARTIFACTS or compression artifacts
   - NO BANDING - use smooth gradients
   - Sharp edges where the subject meets the background
4. DEPTH INTERPRETATION:
   - Analyze the 3D structure of the subject
   - Front-facing surfaces should be brightest
   - Recessed areas and background should be darkest
   - Preserve fine surface details through subtle gradient variations
5. BACKGROUND: The background should be pure black (representing the base/back of the mold)

Output ONLY a clean, high-resolution, noise-free grayscale depth map image."""

    def get_prompt_templates(self) -> dict:
        """Get all prompt templates for frontend display."""
        return {
            "extract_subject": {
                "prompt": self._get_extract_subject_prompt(),
                "model": self.CONTENT_MODEL,
            },
            "generate_image": {
                "prompt": self._get_generate_image_prompt("{user_prompt}"),
                "model": self.CONTENT_MODEL,
            },
            "create_depth_map": {
                "prompt": self._get_depth_map_prompt(),
                "model": self.CONTENT_MODEL,
            },
            "generate_mold": {
                "prompt": "Converting depth map to 3D mesh geometry (local processing)",
                "model": "numpy-stl",
            },
        }

    async def extract_subject(self, base64_image: str) -> ImageResult:
        """
        Extract the main subject from an image and optimize it for candle mold creation.
        Uses Nano Banana Pro (Gemini) for intelligent subject extraction.
        """
        self._ensure_initialized()

        # Start a new session for this processing pipeline
        self._start_session()

        # Decode original image
        original_image = self._decode_image(base64_image)
        self._log_image(original_image, 1, "original")

        # Upscale input image
        image = original_image

        prompt = self._get_extract_subject_prompt()

        try:
            from google.genai import types

            response = await self.client.aio.models.generate_content(
                model=self.CONTENT_MODEL,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/png",
                                    data=self._pil_to_bytes(image),
                                )
                            ),
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        # Decode the result and ensure it's high resolution
                        result_image = Image.open(io.BytesIO(part.inline_data.data))
                        self._log_image(result_image, 3, "extracted_raw")

                        return ImageResult(
                            image_base64=self._encode_image(result_image),
                            prompt_used=prompt,
                            model_used=self.CONTENT_MODEL,
                        )

        except Exception as e:
            print(f"Gemini extraction failed, using enhanced original image: {e}")

        # Fallback: return upscaled original
        self._log_image(image, 3, "extracted_fallback")
        return ImageResult(
            image_base64=self._encode_image(image),
            prompt_used=f"[FALLBACK - Original prompt failed]\n\n{prompt}",
            model_used=f"{self.CONTENT_MODEL} (fallback to original)",
        )

    async def generate_image_from_prompt(self, user_prompt: str) -> ImageResult:
        """
        Generate an image from a text prompt, optimized for candle mold creation.
        Uses Gemini's image generation capabilities.
        """
        self._ensure_initialized()

        # Start a new session for this processing pipeline
        self._start_session()

        prompt = self._get_generate_image_prompt(user_prompt)

        try:
            from google.genai import types

            # Use Gemini model with image output modality
            response = await self.client.aio.models.generate_content(
                model=self.CONTENT_MODEL,
                contents=[types.Content(parts=[types.Part(text=prompt)])],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        result_image = Image.open(io.BytesIO(part.inline_data.data))
                        self._log_image(result_image, 1, "generated_raw")

                        return ImageResult(
                            image_base64=self._encode_image(result_image),
                            prompt_used=prompt,
                            model_used=self.CONTENT_MODEL,
                        )

        except Exception as e:
            raise ValueError(f"Failed to generate image from prompt: {e}")

        raise ValueError("Failed to generate image from prompt")

    async def create_depth_map(self, base64_image: str) -> ImageResult:
        """
        Create a depth map from an image using Nano Banana Pro.
        The depth map represents the 3D relief that will become the candle shape.
        """
        self._ensure_initialized()
        image = self._decode_image(base64_image)

        prompt = self._get_depth_map_prompt()

        try:
            from google.genai import types

            response = await self.client.aio.models.generate_content(
                model=self.CONTENT_MODEL,
                contents=[
                    types.Content(
                        parts=[
                            types.Part(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/png",
                                    data=self._pil_to_bytes(image),
                                )
                            ),
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                ),
            )

            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "inline_data") and part.inline_data:
                        # Convert to grayscale depth map
                        depth_image = Image.open(io.BytesIO(part.inline_data.data)).convert("L")
                        self._log_image(depth_image, 5, "depth_map_raw")

                        return ImageResult(
                            image_base64=self._encode_image(depth_image),
                            prompt_used=prompt,
                            model_used=self.CONTENT_MODEL,
                        )

        except Exception as e:
            print(f"Gemini depth map failed, using fallback: {e}")

        return self._generate_simple_depth_map(image, prompt)

    def _smooth_depth_map(self, depth_image: Image.Image) -> Image.Image:
        """Apply smoothing to reduce noise in depth map while preserving edges."""
        import numpy as np
        from scipy import ndimage

        depth_array = np.array(depth_image, dtype=np.float32)

        # Apply bilateral-like filtering: smooth while preserving edges
        # First, apply a gentle gaussian blur
        smoothed = ndimage.gaussian_filter(depth_array, sigma=1.5)

        # Blend with original to preserve some detail
        result = 0.7 * smoothed + 0.3 * depth_array

        # Enhance contrast
        result = (result - result.min()) / (result.max() - result.min() + 1e-8) * 255

        return Image.fromarray(result.astype(np.uint8))

    def _upscale_to_4k(self, image: Image.Image, min_size: int = 3840) -> Image.Image:
        """
        Upscale image to at least 4K resolution using LANCZOS resampling.

        Args:
            image: PIL Image to upscale
            min_size: Minimum size for the longest edge (default 3840 for 4K)

        Returns:
            Upscaled PIL Image, or original if already >= min_size
        """
        width, height = image.size
        longest_edge = max(width, height)

        if longest_edge >= min_size:
            print(f"[Upscale] Image already {width}x{height}, no upscaling needed")
            return image

        # Calculate scale factor to reach min_size on longest edge
        scale_factor = min_size / longest_edge
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)

        print(f"[Upscale] Scaling from {width}x{height} to {new_width}x{new_height} (factor: {scale_factor:.2f}x)")

        # Use LANCZOS for high-quality upscaling (best for depth maps with smooth gradients)
        upscaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return upscaled

    def _generate_simple_depth_map(self, image: Image.Image, original_prompt: str) -> ImageResult:
        """Fallback: generate a depth map based on luminance with smoothing."""
        import numpy as np
        from scipy import ndimage

        # Convert to grayscale
        grayscale = image.convert("L")

        self._log_image(grayscale, 5, "depth_map_fallback_grayscale")

        # Apply smoothing
        depth_array = np.array(grayscale, dtype=np.float32)
        smoothed = ndimage.gaussian_filter(depth_array, sigma=2.0)

        # Normalize
        smoothed = (smoothed - smoothed.min()) / (smoothed.max() - smoothed.min() + 1e-8) * 255

        result = Image.fromarray(smoothed.astype(np.uint8))
        self._log_image(result, 6, "depth_map_fallback_smoothed")

        # Upscale to 4K if needed
        result = self._upscale_to_4k(result)
        self._log_image(result, 7, "depth_map_fallback_4k")

        return ImageResult(
            image_base64=self._encode_image(result),
            prompt_used=f"[FALLBACK - Luminance-based depth map]\n\nOriginal prompt:\n{original_prompt}",
            model_used="Local processing (grayscale + gaussian smoothing + 4K upscale)",
        )


gemini_service = GeminiService()
