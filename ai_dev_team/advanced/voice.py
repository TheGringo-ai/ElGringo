"""
Voice-to-Code Pipeline - Speak Your Code Into Existence

SECRET WEAPON #5: Voice-controlled coding! Speak naturally and get code.
This uses OpenAI's Whisper for transcription and the AI team for code generation.

Features:
- Real-time speech transcription
- Natural language to code conversion
- Voice commands for editing
- Hands-free coding experience
- Multi-language support

Perfect for:
- Accessibility
- Faster prototyping
- Coding while thinking out loud
- Pair programming with AI
"""

import asyncio
import io
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from voice transcription"""
    text: str
    language: str
    confidence: float
    duration: float


@dataclass
class VoiceCodeResult:
    """Result from voice-to-code"""
    transcription: str
    code: str
    language: str
    explanation: str
    processing_time: float


class VoiceToCodePipeline:
    """
    Voice-to-Code Pipeline

    Transcribe speech and convert to code using the AI team.

    Usage:
        voice = VoiceToCodePipeline()

        # From audio file
        result = await voice.transcribe_and_code("recording.mp3")

        # Real-time (requires microphone)
        async for result in voice.stream_voice_to_code():
            print(result.code)

        # Voice commands
        result = await voice.execute_voice_command(
            "Create a function that validates email addresses"
        )
    """

    # Supported audio formats
    SUPPORTED_FORMATS = {'.mp3', '.mp4', '.m4a', '.wav', '.webm', '.ogg', '.flac'}

    def __init__(self):
        self._openai_client = None
        self._anthropic_client = None

    async def _get_openai_client(self):
        """Get OpenAI client for Whisper"""
        if self._openai_client is None:
            try:
                import openai
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self._openai_client = openai.AsyncOpenAI(api_key=api_key)
            except ImportError:
                logger.error("OpenAI SDK not installed")
        return self._openai_client

    async def _get_anthropic_client(self):
        """Get Anthropic client for code generation"""
        if self._anthropic_client is None:
            try:
                import anthropic
                api_key = os.getenv("ANTHROPIC_API_KEY")
                if api_key:
                    self._anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                pass
        return self._anthropic_client

    async def transcribe(
        self,
        audio: bytes | str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio to text using Whisper.

        Args:
            audio: Audio file path or bytes
            language: Optional language code (e.g., 'en', 'es')

        Returns:
            TranscriptionResult with transcribed text
        """
        client = await self._get_openai_client()
        if not client:
            return TranscriptionResult(
                text="Voice transcription requires OPENAI_API_KEY",
                language="unknown",
                confidence=0.0,
                duration=0.0
            )

        start_time = time.time()

        # Handle file path or bytes
        if isinstance(audio, str):
            audio_path = Path(audio)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio}")

            suffix = audio_path.suffix.lower()
            if suffix not in self.SUPPORTED_FORMATS:
                raise ValueError(f"Unsupported format: {suffix}")

            audio_file = open(audio_path, 'rb')
        else:
            # Create temp file for bytes
            audio_file = io.BytesIO(audio)
            audio_file.name = "audio.mp3"

        try:
            # Use Whisper API
            kwargs = {"model": "whisper-1", "file": audio_file}
            if language:
                kwargs["language"] = language

            response = await client.audio.transcriptions.create(**kwargs)

            return TranscriptionResult(
                text=response.text,
                language=language or "auto",
                confidence=0.95,  # Whisper is generally very accurate
                duration=time.time() - start_time
            )

        finally:
            if isinstance(audio, str):
                audio_file.close()

    async def transcribe_and_code(
        self,
        audio: bytes | str,
        target_language: str = "python",
        context: str = ""
    ) -> VoiceCodeResult:
        """
        Transcribe audio and convert the spoken request to code.

        This is the main function - speak what you want, get code!

        Args:
            audio: Audio file path or bytes
            target_language: Programming language for output
            context: Optional context (existing code, project info)

        Returns:
            VoiceCodeResult with transcription and generated code
        """
        start_time = time.time()

        # Step 1: Transcribe
        transcription = await self.transcribe(audio)
        logger.info(f"Transcribed: {transcription.text[:100]}...")

        # Step 2: Generate code from transcription
        client = await self._get_anthropic_client()
        if not client:
            # Fallback to OpenAI for code generation
            client = await self._get_openai_client()
            if not client:
                return VoiceCodeResult(
                    transcription=transcription.text,
                    code="# Code generation requires API key",
                    language=target_language,
                    explanation="No AI provider available",
                    processing_time=time.time() - start_time
                )

        context_str = f"\nExisting context:\n{context}\n" if context else ""

        prompt = f"""Convert this spoken request into {target_language} code.

Spoken request: "{transcription.text}"
{context_str}

Provide:
1. The code implementation
2. Brief explanation of what it does
3. Any assumptions made

Format your response as:
```{target_language}
[code here]
```

Explanation: [your explanation]"""

        if hasattr(client, 'messages'):  # Anthropic
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                system="You are an expert programmer. Convert spoken requests into clean, well-documented code.",
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text
        else:  # OpenAI
            response = await client.chat.completions.create(
                model="gpt-4o",
                max_tokens=4000,
                messages=[
                    {"role": "system", "content": "You are an expert programmer. Convert spoken requests into clean, well-documented code."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.choices[0].message.content

        # Extract code and explanation
        code = self._extract_code(response_text, target_language)
        explanation = self._extract_explanation(response_text)

        return VoiceCodeResult(
            transcription=transcription.text,
            code=code,
            language=target_language,
            explanation=explanation,
            processing_time=time.time() - start_time
        )

    def _extract_code(self, text: str, language: str) -> str:
        """Extract code block from response"""
        import re

        # Try to find code block with language
        pattern = rf'```{language}\n(.*?)```'
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # Try generic code block
        pattern = r'```\n?(.*?)```'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return text

    def _extract_explanation(self, text: str) -> str:
        """Extract explanation from response"""
        if "Explanation:" in text:
            return text.split("Explanation:")[-1].strip()
        if "```" in text:
            parts = text.split("```")
            if len(parts) > 2:
                return parts[-1].strip()
        return ""

    async def execute_voice_command(
        self,
        command: str,
        current_code: str = "",
        language: str = "python"
    ) -> VoiceCodeResult:
        """
        Execute a voice command on code.

        Voice commands supported:
        - "Create a function that..."
        - "Add error handling to..."
        - "Refactor this to..."
        - "Add tests for..."
        - "Document this code"
        - "Optimize the performance of..."

        Args:
            command: The voice command text
            current_code: Existing code to modify
            language: Target programming language

        Returns:
            VoiceCodeResult with the result
        """
        start_time = time.time()

        client = await self._get_anthropic_client()
        if not client:
            return VoiceCodeResult(
                transcription=command,
                code="# Requires ANTHROPIC_API_KEY",
                language=language,
                explanation="",
                processing_time=0
            )

        if current_code:
            prompt = f"""Execute this voice command on the provided code:

Voice command: "{command}"

Current code:
```{language}
{current_code}
```

Provide the updated code with the requested changes."""
        else:
            prompt = f"""Execute this voice command:

Voice command: "{command}"

Target language: {language}

Generate the code to fulfill this request."""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system="You are a voice-controlled coding assistant. Execute commands precisely.",
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text
        code = self._extract_code(response_text, language)

        return VoiceCodeResult(
            transcription=command,
            code=code,
            language=language,
            explanation=self._extract_explanation(response_text),
            processing_time=time.time() - start_time
        )

    async def real_time_transcription(
        self,
        audio_stream: AsyncIterator[bytes],
        on_transcript: Callable[[str], None]
    ):
        """
        Real-time transcription from audio stream.

        This would integrate with microphone input for live coding.
        Requires additional setup (pyaudio or similar).

        Args:
            audio_stream: Async iterator of audio chunks
            on_transcript: Callback for each transcription segment
        """
        buffer = io.BytesIO()
        buffer_duration = 0
        CHUNK_DURATION = 5  # Transcribe every 5 seconds

        async for chunk in audio_stream:
            buffer.write(chunk)
            buffer_duration += len(chunk) / 16000 / 2  # Rough duration estimate

            if buffer_duration >= CHUNK_DURATION:
                # Transcribe buffered audio
                buffer.seek(0)
                result = await self.transcribe(buffer.getvalue())
                on_transcript(result.text)

                # Reset buffer
                buffer = io.BytesIO()
                buffer_duration = 0


# Voice command patterns for smart execution
VOICE_COMMAND_PATTERNS = {
    r"create (?:a )?function": "create_function",
    r"add (?:a )?class": "create_class",
    r"write tests?": "write_tests",
    r"add (?:error )?handling": "add_error_handling",
    r"refactor": "refactor",
    r"optimize": "optimize",
    r"document": "add_documentation",
    r"explain": "explain_code",
    r"debug": "debug",
    r"fix": "fix_bug",
}


# Convenience functions
async def voice_to_code(audio_path: str, language: str = "python") -> str:
    """Quick voice to code conversion"""
    pipeline = VoiceToCodePipeline()
    result = await pipeline.transcribe_and_code(audio_path, language)
    return result.code


async def voice_command(command: str, code: str = "", language: str = "python") -> str:
    """Execute a voice command"""
    pipeline = VoiceToCodePipeline()
    result = await pipeline.execute_voice_command(command, code, language)
    return result.code


class VoiceInput:
    """
    Real-time voice input from microphone.

    Uses speech_recognition library for microphone access
    and OpenAI Whisper for high-quality transcription.
    """

    def __init__(self, language: str = "en", timeout: int = 10):
        self.language = language
        self.timeout = timeout
        self._recognizer = None
        self._microphone = None

    def _init_audio(self) -> bool:
        """Initialize audio components"""
        if self._recognizer is not None:
            return True

        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._microphone = sr.Microphone()

            # Calibrate for ambient noise
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

            return True
        except ImportError:
            logger.error("speech_recognition not installed. Run: pip install SpeechRecognition pyaudio")
            return False
        except Exception as e:
            logger.error(f"Microphone init failed: {e}")
            return False

    async def listen(self, prompt: str = None) -> TranscriptionResult:
        """
        Listen to microphone and transcribe speech.

        Args:
            prompt: Optional prompt to show user

        Returns:
            TranscriptionResult with transcribed text
        """
        if not self._init_audio():
            return TranscriptionResult(
                text="",
                language=self.language,
                confidence=0.0,
                duration=0.0
            )

        import speech_recognition as sr

        if prompt:
            print(prompt)

        print("Listening... (speak now)")
        start_time = time.time()

        try:
            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=self.timeout,
                    phrase_time_limit=15
                )
        except sr.WaitTimeoutError:
            print("No speech detected")
            return TranscriptionResult(
                text="",
                language=self.language,
                confidence=0.0,
                duration=time.time() - start_time
            )

        print("Processing...")

        # Try Whisper API first (best quality)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                result = await self._transcribe_whisper(audio, api_key)
                result.duration = time.time() - start_time
                return result
            except Exception as e:
                logger.warning(f"Whisper failed: {e}, trying Google")

        # Fallback to Google Speech Recognition
        try:
            text = await asyncio.to_thread(
                self._recognizer.recognize_google,
                audio,
                language=self.language
            )
            return TranscriptionResult(
                text=text,
                language=self.language,
                confidence=0.85,
                duration=time.time() - start_time
            )
        except sr.UnknownValueError:
            return TranscriptionResult(
                text="",
                language=self.language,
                confidence=0.0,
                duration=time.time() - start_time
            )
        except sr.RequestError as e:
            logger.error(f"Speech recognition error: {e}")
            return TranscriptionResult(
                text="",
                language=self.language,
                confidence=0.0,
                duration=time.time() - start_time
            )

    async def _transcribe_whisper(self, audio, api_key: str) -> TranscriptionResult:
        """Transcribe audio using Whisper API"""
        import openai

        # Save audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio.get_wav_data())
            audio_path = f.name

        try:
            client = openai.OpenAI(api_key=api_key)

            with open(audio_path, "rb") as audio_file:
                response = await asyncio.to_thread(
                    client.audio.transcriptions.create,
                    model="whisper-1",
                    file=audio_file,
                    language=self.language.split("-")[0]
                )

            return TranscriptionResult(
                text=response.text,
                language=self.language,
                confidence=0.95,
                duration=0.0
            )
        finally:
            os.unlink(audio_path)

    async def listen_for_command(self) -> str:
        """Listen and return command text"""
        result = await self.listen("Speak your command...")
        return result.text

    async def listen_continuous(
        self,
        callback: Callable[[str], None],
        stop_phrase: str = "stop listening"
    ):
        """
        Continuously listen and call callback with transcriptions.

        Args:
            callback: Function to call with each transcription
            stop_phrase: Say this to stop listening
        """
        print(f"Continuous listening mode. Say '{stop_phrase}' to stop.")

        while True:
            result = await self.listen()

            if not result.text:
                continue

            if stop_phrase.lower() in result.text.lower():
                print("Stopping voice input...")
                break

            callback(result.text)


# Quick access function
async def listen_once(prompt: str = None) -> str:
    """Quick one-shot voice input"""
    voice = VoiceInput()
    result = await voice.listen(prompt)
    return result.text
