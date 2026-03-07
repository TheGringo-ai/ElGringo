"""
Vision Engine - Screenshot-to-Code & Image Understanding

SECRET WEAPON #2: All major AI models now support vision/images!
This enables incredible capabilities:

- Screenshot-to-Code: Paste a UI image, get the implementation
- Bug Detection: Show error screenshots, get fixes
- Architecture Diagrams: Understand and implement from diagrams
- Code Review: Analyze code screenshots
- UI/UX Analysis: Get design feedback from mockups

Most developers don't know they can just paste images into AI!
"""

import base64
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class VisionResult:
    """Result from vision analysis"""
    description: str
    code: Optional[str] = None
    suggestions: List[str] = None
    confidence: float = 0.0
    model_used: str = ""
    processing_time: float = 0.0
    image_dimensions: Optional[tuple] = None


class VisionEngine:
    """
    Multi-Model Vision Engine

    Supports:
    - Claude (claude-sonnet-4-20250514) - Best for code generation
    - GPT-4o - Great for UI understanding
    - Gemini 2.5 Flash - Fast and good quality
    - Grok - Vision capable

    Usage:
        engine = VisionEngine()

        # From file path
        result = await engine.analyze_image("/path/to/screenshot.png",
            prompt="Convert this UI to React components")

        # From base64
        result = await engine.analyze_image(base64_data,
            prompt="What's in this image?")

        # From URL
        result = await engine.analyze_url("https://example.com/image.png",
            prompt="Describe this diagram")
    """

    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}

    def __init__(self, preferred_model: str = "claude"):
        """
        Initialize vision engine.

        Args:
            preferred_model: "claude", "gpt4", "gemini", or "grok"
        """
        self.preferred_model = preferred_model
        self._clients = {}

    async def _get_claude_client(self):
        """Get Anthropic client"""
        if "claude" not in self._clients:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._clients["claude"] = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                pass
        return self._clients.get("claude")

    async def _get_openai_client(self):
        """Get OpenAI client"""
        if "openai" not in self._clients:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._clients["openai"] = openai.AsyncOpenAI(api_key=api_key)
            except ImportError:
                pass
        return self._clients.get("openai")

    async def _get_gemini_client(self):
        """Get Gemini client"""
        if "gemini" not in self._clients:
            try:
                from google import genai
                api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if api_key:
                    self._clients["gemini"] = genai.Client(api_key=api_key)
            except ImportError:
                pass
        return self._clients.get("gemini")

    def _load_image_as_base64(self, image_path: str) -> tuple:
        """Load image file and convert to base64"""
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {suffix}")

        media_type = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }[suffix]

        with open(path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')

        return image_data, media_type

    async def analyze_image(
        self,
        image: Union[str, bytes],
        prompt: str,
        model: Optional[str] = None,
        extract_code: bool = True
    ) -> VisionResult:
        """
        Analyze an image with AI vision.

        Args:
            image: File path, base64 string, or bytes
            prompt: What to analyze/generate
            model: Override preferred model
            extract_code: Try to extract code blocks from response

        Returns:
            VisionResult with description, code, and suggestions
        """
        start_time = time.time()
        model = model or self.preferred_model

        # Load image
        if isinstance(image, bytes):
            image_data = base64.standard_b64encode(image).decode('utf-8')
            media_type = "image/png"  # Assume PNG for bytes
        elif os.path.isfile(image):
            image_data, media_type = self._load_image_as_base64(image)
        else:
            # Assume it's already base64
            image_data = image
            media_type = "image/png"

        # Try preferred model, fall back to others
        result = None
        models_to_try = [model]
        if model != "claude":
            models_to_try.append("claude")
        if model != "gpt4":
            models_to_try.append("gpt4")
        if model != "gemini":
            models_to_try.append("gemini")

        for try_model in models_to_try:
            try:
                if try_model == "claude":
                    result = await self._analyze_with_claude(image_data, media_type, prompt)
                elif try_model == "gpt4":
                    result = await self._analyze_with_gpt4(image_data, media_type, prompt)
                elif try_model == "gemini":
                    result = await self._analyze_with_gemini(image_data, prompt)

                if result and result.description:
                    result.model_used = try_model
                    break
            except Exception as e:
                logger.warning(f"Vision with {try_model} failed: {e}")
                continue

        if not result:
            return VisionResult(
                description="Vision analysis failed - no models available",
                confidence=0.0,
                processing_time=time.time() - start_time
            )

        # Extract code if requested
        if extract_code and result.description:
            result.code = self._extract_code_blocks(result.description)

        result.processing_time = time.time() - start_time
        return result

    async def _analyze_with_claude(
        self,
        image_data: str,
        media_type: str,
        prompt: str
    ) -> VisionResult:
        """Analyze image with Claude"""
        client = await self._get_claude_client()
        if not client:
            raise RuntimeError("Claude client not available")

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        return VisionResult(
            description=response.content[0].text,
            confidence=0.9,
            model_used="claude"
        )

    async def _analyze_with_gpt4(
        self,
        image_data: str,
        media_type: str,
        prompt: str
    ) -> VisionResult:
        """Analyze image with GPT-4o"""
        client = await self._get_openai_client()
        if not client:
            raise RuntimeError("OpenAI client not available")

        response = await client.chat.completions.create(
            model="gpt-4o",
            max_tokens=8000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{image_data}"
                        }
                    }
                ]
            }]
        )

        return VisionResult(
            description=response.choices[0].message.content,
            confidence=0.9,
            model_used="gpt4"
        )

    async def _analyze_with_gemini(
        self,
        image_data: str,
        prompt: str
    ) -> VisionResult:
        """Analyze image with Gemini"""
        client = await self._get_gemini_client()
        if not client:
            raise RuntimeError("Gemini client not available")

        # Decode base64 to bytes for Gemini
        from google.genai import types
        image_bytes = base64.b64decode(image_data)

        image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/png")
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, image_part],
        )

        return VisionResult(
            description=response.text,
            confidence=0.85,
            model_used="gemini"
        )

    def _extract_code_blocks(self, text: str) -> Optional[str]:
        """Extract code blocks from markdown response"""
        import re

        # Find all code blocks
        pattern = r'```(?:\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        if matches:
            return '\n\n'.join(matches)
        return None

    async def screenshot_to_code(
        self,
        image: Union[str, bytes],
        framework: str = "react",
        style: str = "tailwind"
    ) -> VisionResult:
        """
        Convert a UI screenshot to code.

        This is the killer feature! Paste any UI design and get
        working code in your preferred framework.

        Args:
            image: Screenshot path, bytes, or base64
            framework: "react", "vue", "svelte", "html"
            style: "tailwind", "css", "styled-components"

        Returns:
            VisionResult with generated code
        """
        prompt = f"""Analyze this UI screenshot and generate production-ready code.

Framework: {framework}
Styling: {style}

Requirements:
1. Match the visual design as closely as possible
2. Use semantic HTML elements
3. Include responsive design
4. Add appropriate accessibility attributes
5. Use modern best practices
6. Include component structure if applicable

Generate the complete, ready-to-use code."""

        return await self.analyze_image(image, prompt, extract_code=True)

    async def analyze_error_screenshot(
        self,
        image: Union[str, bytes]
    ) -> VisionResult:
        """
        Analyze an error screenshot and suggest fixes.

        Take a screenshot of an error message or broken UI
        and get debugging suggestions.
        """
        prompt = """Analyze this error screenshot and provide:

1. What the error is
2. Likely causes
3. Step-by-step fix instructions
4. Code changes needed (if applicable)
5. How to prevent this in the future

Be specific and actionable."""

        return await self.analyze_image(image, prompt)

    async def analyze_architecture_diagram(
        self,
        image: Union[str, bytes]
    ) -> VisionResult:
        """
        Analyze an architecture diagram and generate implementation plan.
        """
        prompt = """Analyze this architecture/system diagram and provide:

1. Component inventory (list all components shown)
2. Data flow description
3. Implementation order (what to build first)
4. Technology recommendations
5. Potential issues or concerns
6. Starter code for key components

Be thorough and practical."""

        return await self.analyze_image(image, prompt)

    async def compare_designs(
        self,
        image1: Union[str, bytes],
        image2: Union[str, bytes]
    ) -> str:
        """Compare two design screenshots and identify differences"""
        # This would require a more complex implementation
        # For now, analyze them separately
        result1 = await self.analyze_image(image1, "Describe this UI in detail")
        result2 = await self.analyze_image(image2, "Describe this UI in detail")

        # Use text comparison
        client = await self._get_claude_client()
        if client:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[{
                    "role": "user",
                    "content": f"""Compare these two UI descriptions and identify:
1. Visual differences
2. Missing elements
3. Layout changes
4. Style differences

Design 1:
{result1.description}

Design 2:
{result2.description}

Provide a detailed comparison."""
                }]
            )
            return response.content[0].text

        return f"Design 1: {result1.description}\n\nDesign 2: {result2.description}"


# Convenience functions
async def screenshot_to_react(image_path: str) -> str:
    """Quick screenshot to React code"""
    engine = VisionEngine(preferred_model="claude")
    result = await engine.screenshot_to_code(image_path, framework="react")
    return result.code or result.description


async def analyze_screenshot(image_path: str, question: str) -> str:
    """Quick image analysis"""
    engine = VisionEngine()
    result = await engine.analyze_image(image_path, question)
    return result.description
