"""
Text-to-Speech engine for Jarvis AI Assistant.
Supports multiple TTS backends including Silero, Bark, and pyttsx3.
"""

import asyncio
import io
import tempfile
import threading
from typing import Optional, Dict, Any
import numpy as np
import sounddevice as sd
import queue
import time
from pathlib import Path

try:
    import torch
    import torchaudio
    from TTS.api import TTS
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False

try:
    from bark import SAMPLE_RATE, generate_audio, preload_models
    BARK_AVAILABLE = True
except ImportError:
    BARK_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from ..core.config import config
from ..core.logging import get_logger, log_performance

logger = get_logger("tts_engine")


class SileroTTS:
    """Silero TTS implementation."""
    
    def __init__(self):
        self.model = None
        self.device = None
        self.sample_rate = 48000
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Silero TTS."""
        try:
            if not SILERO_AVAILABLE:
                logger.error("Silero TTS dependencies not available")
                return False
            
            # Set device
            self.device = torch.device('cuda' if torch.cuda.is_available() and config.performance.gpu_acceleration else 'cpu')
            
            # Load model
            model_name = 'v3_en'  # English model
            self.model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-models',
                model='silero_tts',
                language='en',
                speaker=model_name
            )
            
            self.model.to(self.device)
            
            logger.info(f"Silero TTS initialized on {self.device}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Silero TTS: {e}")
            return False
    
    async def synthesize(self, text: str, voice: str = "en_v6") -> Optional[np.ndarray]:
        """Synthesize speech from text."""
        if not self.initialized:
            return None
        
        try:
            with log_performance(logger, "Silero TTS synthesis"):
                # Run synthesis in thread pool
                loop = asyncio.get_event_loop()
                audio = await loop.run_in_executor(
                    None,
                    self._synthesize_sync,
                    text,
                    voice
                )
                
                return audio
                
        except Exception as e:
            logger.error(f"Error in Silero TTS synthesis: {e}")
            return None
    
    def _synthesize_sync(self, text: str, voice: str) -> Optional[np.ndarray]:
        """Synchronous synthesis."""
        try:
            # Apply model
            audio = self.model.apply_tts(
                text=text,
                speaker=voice,
                sample_rate=self.sample_rate
            )
            
            # Convert to numpy array
            if isinstance(audio, torch.Tensor):
                audio = audio.cpu().numpy()
            
            return audio
            
        except Exception as e:
            logger.error(f"Error in synchronous synthesis: {e}")
            return None


class BarkTTS:
    """Bark TTS implementation."""
    
    def __init__(self):
        self.initialized = False
        self.sample_rate = 24000
    
    async def initialize(self) -> bool:
        """Initialize Bark TTS."""
        try:
            if not BARK_AVAILABLE:
                logger.error("Bark TTS dependencies not available")
                return False
            
            # Preload models in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, preload_models)
            
            logger.info("Bark TTS initialized")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Bark TTS: {e}")
            return False
    
    async def synthesize(self, text: str, voice: str = "v2/en_speaker_0") -> Optional[np.ndarray]:
        """Synthesize speech from text."""
        if not self.initialized:
            return None
        
        try:
            with log_performance(logger, "Bark TTS synthesis"):
                # Run synthesis in thread pool
                loop = asyncio.get_event_loop()
                audio = await loop.run_in_executor(
                    None,
                    self._synthesize_sync,
                    text,
                    voice
                )
                
                return audio
                
        except Exception as e:
            logger.error(f"Error in Bark TTS synthesis: {e}")
            return None
    
    def _synthesize_sync(self, text: str, voice: str) -> Optional[np.ndarray]:
        """Synchronous synthesis."""
        try:
            # Generate audio
            audio_array = generate_audio(text, history_prompt=voice)
            
            # Normalize audio
            audio_array = audio_array / np.max(np.abs(audio_array))
            
            return audio_array
            
        except Exception as e:
            logger.error(f"Error in synchronous synthesis: {e}")
            return None


class Pyttsx3TTS:
    """pyttsx3 TTS implementation."""
    
    def __init__(self):
        self.engine = None
        self.initialized = False
        self.temp_files = []
    
    async def initialize(self) -> bool:
        """Initialize pyttsx3 TTS."""
        try:
            if not PYTTSX3_AVAILABLE:
                logger.error("pyttsx3 TTS dependencies not available")
                return False
            
            # Initialize engine in thread pool
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(None, self._init_engine)
            
            if success:
                logger.info("pyttsx3 TTS initialized")
                self.initialized = True
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3 TTS: {e}")
            return False
    
    def _init_engine(self) -> bool:
        """Initialize pyttsx3 engine synchronously."""
        try:
            self.engine = pyttsx3.init()
            
            # Configure voice settings
            voices = self.engine.getProperty('voices')
            if voices:
                # Try to find a good English voice
                for voice in voices:
                    if 'english' in voice.name.lower() or 'en' in voice.id.lower():
                        self.engine.setProperty('voice', voice.id)
                        break
            
            # Set speech rate and volume
            self.engine.setProperty('rate', 200)  # Speed
            self.engine.setProperty('volume', 0.9)  # Volume
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing pyttsx3 engine: {e}")
            return False
    
    async def synthesize(self, text: str, voice: str = None) -> Optional[np.ndarray]:
        """Synthesize speech from text."""
        if not self.initialized:
            return None
        
        try:
            with log_performance(logger, "pyttsx3 TTS synthesis"):
                # Run synthesis in thread pool
                loop = asyncio.get_event_loop()
                audio_file = await loop.run_in_executor(
                    None,
                    self._synthesize_to_file,
                    text
                )
                
                if audio_file:
                    # Load audio file
                    audio = await self._load_audio_file(audio_file)
                    return audio
                
                return None
                
        except Exception as e:
            logger.error(f"Error in pyttsx3 TTS synthesis: {e}")
            return None
    
    def _synthesize_to_file(self, text: str) -> Optional[str]:
        """Synthesize speech to temporary file."""
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_file.close()
            
            # Save to file
            self.engine.save_to_file(text, temp_file.name)
            self.engine.runAndWait()
            
            self.temp_files.append(temp_file.name)
            return temp_file.name
            
        except Exception as e:
            logger.error(f"Error synthesizing to file: {e}")
            return None
    
    async def _load_audio_file(self, file_path: str) -> Optional[np.ndarray]:
        """Load audio from file."""
        try:
            import wave
            
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.readframes(-1)
                sample_rate = wav_file.getframerate()
                
                # Convert to numpy array
                audio = np.frombuffer(frames, dtype=np.int16)
                
                # Convert to float32 and normalize
                audio = audio.astype(np.float32) / 32768.0
                
                return audio
                
        except Exception as e:
            logger.error(f"Error loading audio file: {e}")
            return None
    
    def cleanup(self) -> None:
        """Cleanup temporary files."""
        for temp_file in self.temp_files:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except:
                pass
        self.temp_files.clear()


class AudioPlayer:
    """Audio playback manager."""
    
    def __init__(self):
        self.current_stream = None
        self.playing = False
        self.play_queue = queue.Queue()
        self.stop_event = threading.Event()
    
    async def play_audio(self, audio_data: np.ndarray, sample_rate: int = 22050) -> None:
        """Play audio data."""
        try:
            if audio_data is None or len(audio_data) == 0:
                return
            
            # Stop any current playback
            await self.stop_playback()
            
            # Play audio in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._play_audio_sync,
                audio_data,
                sample_rate
            )
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
    
    def _play_audio_sync(self, audio_data: np.ndarray, sample_rate: int) -> None:
        """Play audio synchronously."""
        try:
            self.playing = True
            
            # Ensure audio is in correct format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # Normalize if needed
            if np.max(np.abs(audio_data)) > 1.0:
                audio_data = audio_data / np.max(np.abs(audio_data))
            
            # Play audio
            sd.play(audio_data, samplerate=sample_rate)
            sd.wait()  # Wait until playback is finished
            
        except Exception as e:
            logger.error(f"Error in synchronous audio playback: {e}")
        finally:
            self.playing = False
    
    async def stop_playback(self) -> None:
        """Stop current audio playback."""
        try:
            if self.playing:
                sd.stop()
                self.playing = False
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        return self.playing


class TTSEngine:
    """Main Text-to-Speech engine."""
    
    def __init__(self):
        self.engine_type = config.voice.tts_engine
        self.voice = config.voice.tts_voice
        
        # TTS backends
        self.silero_tts = None
        self.bark_tts = None
        self.pyttsx3_tts = None
        
        # Audio player
        self.audio_player = AudioPlayer()
        
        # Current engine
        self.current_engine = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize TTS engine."""
        try:
            logger.info(f"Initializing TTS engine: {self.engine_type}")
            
            if self.engine_type == "silero" and SILERO_AVAILABLE:
                self.silero_tts = SileroTTS()
                if await self.silero_tts.initialize():
                    self.current_engine = self.silero_tts
                    self.initialized = True
                    return True
            
            elif self.engine_type == "bark" and BARK_AVAILABLE:
                self.bark_tts = BarkTTS()
                if await self.bark_tts.initialize():
                    self.current_engine = self.bark_tts
                    self.initialized = True
                    return True
            
            elif self.engine_type == "pyttsx3" and PYTTSX3_AVAILABLE:
                self.pyttsx3_tts = Pyttsx3TTS()
                if await self.pyttsx3_tts.initialize():
                    self.current_engine = self.pyttsx3_tts
                    self.initialized = True
                    return True
            
            # Fallback to pyttsx3 if primary engine fails
            if not self.initialized and PYTTSX3_AVAILABLE:
                logger.warning(f"Primary TTS engine '{self.engine_type}' failed, falling back to pyttsx3")
                self.pyttsx3_tts = Pyttsx3TTS()
                if await self.pyttsx3_tts.initialize():
                    self.current_engine = self.pyttsx3_tts
                    self.initialized = True
                    return True
            
            logger.error("No TTS engine could be initialized")
            return False
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            return False
    
    async def speak(self, text: str, interrupt: bool = True) -> bool:
        """Speak the given text."""
        if not self.initialized or not self.current_engine:
            logger.warning("TTS engine not initialized")
            return False
        
        try:
            # Stop current playback if interrupting
            if interrupt:
                await self.audio_player.stop_playback()
            
            # Skip if already playing and not interrupting
            if not interrupt and self.audio_player.is_playing():
                logger.debug("Audio already playing, skipping")
                return False
            
            # Clean up text
            text = self._clean_text(text)
            if not text:
                return False
            
            logger.debug(f"Speaking: {text[:100]}...")
            
            # Synthesize speech
            audio_data = await self.current_engine.synthesize(text, self.voice)
            
            if audio_data is not None:
                # Determine sample rate based on engine
                sample_rate = self._get_sample_rate()
                
                # Play audio
                await self.audio_player.play_audio(audio_data, sample_rate)
                
                logger.debug("Speech playback completed")
                return True
            else:
                logger.error("Failed to synthesize speech")
                return False
                
        except Exception as e:
            logger.error(f"Error in speech synthesis: {e}")
            return False
    
    def _clean_text(self, text: str) -> str:
        """Clean text for TTS."""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Limit length
        max_length = 1000  # Reasonable limit for TTS
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text.strip()
    
    def _get_sample_rate(self) -> int:
        """Get sample rate for current engine."""
        if isinstance(self.current_engine, SileroTTS):
            return self.current_engine.sample_rate
        elif isinstance(self.current_engine, BarkTTS):
            return self.current_engine.sample_rate
        else:
            return 22050  # Default sample rate
    
    async def stop_speaking(self) -> None:
        """Stop current speech."""
        await self.audio_player.stop_playback()
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self.audio_player.is_playing()
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get available voices for current engine."""
        if not self.initialized:
            return {}
        
        # Return voice information based on engine type
        if self.engine_type == "silero":
            return {
                "engine": "silero",
                "voices": ["en_v6", "en_v5", "en_v4"],
                "current": self.voice
            }
        elif self.engine_type == "bark":
            return {
                "engine": "bark",
                "voices": ["v2/en_speaker_0", "v2/en_speaker_1", "v2/en_speaker_2"],
                "current": self.voice
            }
        elif self.engine_type == "pyttsx3":
            return {
                "engine": "pyttsx3",
                "voices": ["system_default"],
                "current": "system_default"
            }
        
        return {}
    
    def set_voice(self, voice: str) -> bool:
        """Set the voice for TTS."""
        try:
            self.voice = voice
            logger.info(f"TTS voice set to: {voice}")
            return True
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup TTS engine."""
        logger.info("Cleaning up TTS engine...")
        
        # Stop any playback
        try:
            asyncio.create_task(self.audio_player.stop_playback())
        except:
            pass
        
        # Cleanup engines
        if self.pyttsx3_tts:
            self.pyttsx3_tts.cleanup()
        
        self.initialized = False
        logger.info("TTS engine cleanup complete")


# Test function
async def test_tts():
    """Test TTS functionality."""
    tts = TTSEngine()
    
    if await tts.initialize():
        print("TTS initialized successfully")
        print(f"Available voices: {tts.get_available_voices()}")
        
        # Test speech
        await tts.speak("Hello, this is a test of the Jarvis text to speech system.")
        
        tts.cleanup()
    else:
        print("Failed to initialize TTS")


if __name__ == "__main__":
    asyncio.run(test_tts())
