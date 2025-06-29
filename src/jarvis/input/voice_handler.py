"""
Voice input handling for Jarvis AI Assistant.
Includes wake word detection and speech-to-text processing.
"""

import asyncio
import numpy as np
import sounddevice as sd
from typing import Optional, List
import threading
import queue
import time
from pathlib import Path
import tempfile
import wave

try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False

try:
    import openwakeword
    from openwakeword import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

from ..core.config import config
from ..core.logging import get_logger, log_performance

logger = get_logger("voice_handler")


class AudioBuffer:
    """Circular audio buffer for continuous recording."""
    
    def __init__(self, max_duration: float = 30.0, sample_rate: int = 16000):
        self.max_duration = max_duration
        self.sample_rate = sample_rate
        self.max_samples = int(max_duration * sample_rate)
        self.buffer = np.zeros(self.max_samples, dtype=np.float32)
        self.write_pos = 0
        self.lock = threading.Lock()
    
    def write(self, data: np.ndarray) -> None:
        """Write audio data to buffer."""
        with self.lock:
            data_len = len(data)
            
            if data_len >= self.max_samples:
                # Data is larger than buffer, keep only the last part
                self.buffer = data[-self.max_samples:].copy()
                self.write_pos = 0
            else:
                # Check if we need to wrap around
                if self.write_pos + data_len <= self.max_samples:
                    self.buffer[self.write_pos:self.write_pos + data_len] = data
                    self.write_pos = (self.write_pos + data_len) % self.max_samples
                else:
                    # Wrap around
                    first_part = self.max_samples - self.write_pos
                    self.buffer[self.write_pos:] = data[:first_part]
                    self.buffer[:data_len - first_part] = data[first_part:]
                    self.write_pos = data_len - first_part
    
    def read_last(self, duration: float) -> np.ndarray:
        """Read the last N seconds of audio."""
        with self.lock:
            samples = int(duration * self.sample_rate)
            samples = min(samples, self.max_samples)
            
            if samples >= self.max_samples:
                return self.buffer.copy()
            
            # Calculate start position
            start_pos = (self.write_pos - samples) % self.max_samples
            
            if start_pos + samples <= self.max_samples:
                return self.buffer[start_pos:start_pos + samples].copy()
            else:
                # Wrap around
                first_part = self.max_samples - start_pos
                result = np.zeros(samples, dtype=np.float32)
                result[:first_part] = self.buffer[start_pos:]
                result[first_part:] = self.buffer[:samples - first_part]
                return result


class WakeWordDetector:
    """Wake word detection using OpenWakeWord or Porcupine."""
    
    def __init__(self):
        self.engine = config.voice.wake_word_engine
        self.wake_word = config.voice.wake_word
        self.model = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize wake word detection."""
        try:
            if self.engine == "openwakeword" and OPENWAKEWORD_AVAILABLE:
                return await self._init_openwakeword()
            elif self.engine == "porcupine" and PORCUPINE_AVAILABLE:
                return await self._init_porcupine()
            else:
                logger.error(f"Wake word engine '{self.engine}' not available")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize wake word detection: {e}")
            return False
    
    async def _init_openwakeword(self) -> bool:
        """Initialize OpenWakeWord."""
        try:
            # Download models if needed
            openwakeword.utils.download_models()
            
            # Load model based on wake word
            model_name = self._get_openwakeword_model_name()
            self.model = Model(wakeword_models=[model_name])
            
            logger.info(f"OpenWakeWord initialized with model: {model_name}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenWakeWord: {e}")
            return False
    
    async def _init_porcupine(self) -> bool:
        """Initialize Porcupine."""
        try:
            # Map wake word to Porcupine keyword
            keyword = self._get_porcupine_keyword()
            
            self.model = pvporcupine.create(
                keywords=[keyword],
                sensitivities=[config.voice.wake_word_engine == "porcupine" and 0.5 or 0.5]
            )
            
            logger.info(f"Porcupine initialized with keyword: {keyword}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            return False
    
    def _get_openwakeword_model_name(self) -> str:
        """Get OpenWakeWord model name based on wake word."""
        wake_word_lower = self.wake_word.lower().replace(" ", "_")
        
        # Map common wake words to model names
        model_mapping = {
            "hey_max": "hey_jarvis_v0.1",
            "hey_jarvis": "hey_jarvis_v0.1",
            "computer": "alexa_v0.1",  # Use Alexa model as fallback
        }
        
        return model_mapping.get(wake_word_lower, "hey_jarvis_v0.1")
    
    def _get_porcupine_keyword(self) -> str:
        """Get Porcupine keyword based on wake word."""
        wake_word_lower = self.wake_word.lower()
        
        # Map to available Porcupine keywords
        if "jarvis" in wake_word_lower:
            return "jarvis"
        elif "computer" in wake_word_lower:
            return "computer"
        else:
            return "jarvis"  # Default fallback
    
    def detect(self, audio_data: np.ndarray) -> bool:
        """Detect wake word in audio data."""
        if not self.initialized:
            return False
        
        try:
            if self.engine == "openwakeword":
                return self._detect_openwakeword(audio_data)
            elif self.engine == "porcupine":
                return self._detect_porcupine(audio_data)
            return False
            
        except Exception as e:
            logger.error(f"Error in wake word detection: {e}")
            return False
    
    def _detect_openwakeword(self, audio_data: np.ndarray) -> bool:
        """Detect wake word using OpenWakeWord."""
        try:
            # OpenWakeWord expects 16kHz, 16-bit audio
            if len(audio_data) < 1280:  # Minimum chunk size
                return False
            
            # Process audio chunk
            prediction = self.model.predict(audio_data)
            
            # Check if any wake word was detected
            for wake_word, score in prediction.items():
                if score > 0.5:  # Threshold
                    logger.debug(f"Wake word '{wake_word}' detected with score: {score}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in OpenWakeWord detection: {e}")
            return False
    
    def _detect_porcupine(self, audio_data: np.ndarray) -> bool:
        """Detect wake word using Porcupine."""
        try:
            # Porcupine expects 16kHz, 16-bit PCM audio
            # Convert float32 to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Process in chunks of frame_length
            frame_length = self.model.frame_length
            
            for i in range(0, len(audio_int16) - frame_length + 1, frame_length):
                frame = audio_int16[i:i + frame_length]
                keyword_index = self.model.process(frame)
                
                if keyword_index >= 0:
                    logger.debug(f"Wake word detected (keyword index: {keyword_index})")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in Porcupine detection: {e}")
            return False
    
    def cleanup(self) -> None:
        """Cleanup wake word detector."""
        if self.model and self.engine == "porcupine":
            try:
                self.model.delete()
            except:
                pass
        self.model = None
        self.initialized = False


class SpeechToText:
    """Speech-to-text conversion using Whisper or faster-whisper."""
    
    def __init__(self):
        self.engine = config.voice.stt_engine
        self.model_name = config.voice.stt_model
        self.model = None
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Initialize speech-to-text engine."""
        try:
            if self.engine == "faster-whisper" and FASTER_WHISPER_AVAILABLE:
                return await self._init_faster_whisper()
            elif self.engine == "whisper" and WHISPER_AVAILABLE:
                return await self._init_whisper()
            else:
                logger.error(f"STT engine '{self.engine}' not available")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize STT: {e}")
            return False
    
    async def _init_faster_whisper(self) -> bool:
        """Initialize faster-whisper."""
        try:
            # Use GPU if available
            device = "cuda" if config.performance.gpu_acceleration else "cpu"
            
            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type="float16" if device == "cuda" else "int8"
            )
            
            logger.info(f"Faster-Whisper initialized: {self.model_name} on {device}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize faster-whisper: {e}")
            return False
    
    async def _init_whisper(self) -> bool:
        """Initialize OpenAI Whisper."""
        try:
            self.model = whisper.load_model(self.model_name)
            logger.info(f"Whisper initialized: {self.model_name}")
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Whisper: {e}")
            return False
    
    async def transcribe(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe audio data to text."""
        if not self.initialized:
            return None
        
        try:
            with log_performance(logger, "Speech transcription"):
                if self.engine == "faster-whisper":
                    return await self._transcribe_faster_whisper(audio_data)
                elif self.engine == "whisper":
                    return await self._transcribe_whisper(audio_data)
                return None
                
        except Exception as e:
            logger.error(f"Error in speech transcription: {e}")
            return None
    
    async def _transcribe_faster_whisper(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe using faster-whisper."""
        try:
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(audio_data, language="en")
            )
            
            # Combine segments
            text = " ".join([segment.text.strip() for segment in segments])
            
            if text and len(text.strip()) > 0:
                logger.debug(f"Transcribed: {text}")
                return text.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error in faster-whisper transcription: {e}")
            return None
    
    async def _transcribe_whisper(self, audio_data: np.ndarray) -> Optional[str]:
        """Transcribe using OpenAI Whisper."""
        try:
            # Run transcription in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(audio_data, language="en")
            )
            
            text = result["text"].strip()
            
            if text and len(text) > 0:
                logger.debug(f"Transcribed: {text}")
                return text
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Whisper transcription: {e}")
            return None


class VoiceActivityDetector:
    """Voice activity detection using WebRTC VAD or simple volume-based fallback."""
    
    def __init__(self):
        self.sample_rate = config.voice.sample_rate
        self.frame_duration = 30  # ms
        self.frame_size = int(self.sample_rate * self.frame_duration / 1000)
        
        # Initialize WebRTC VAD if available
        if WEBRTCVAD_AVAILABLE:
            try:
                self.vad = webrtcvad.Vad(2)  # Aggressiveness level 0-3
                self.use_webrtc = True
                logger.info("Using WebRTC VAD for voice activity detection")
            except Exception as e:
                logger.warning(f"Failed to initialize WebRTC VAD: {e}")
                self.vad = None
                self.use_webrtc = False
        else:
            logger.info("WebRTC VAD not available, using simple volume-based detection")
            self.vad = None
            self.use_webrtc = False
        
        # Fallback parameters for simple VAD
        self.volume_threshold = 0.01  # Minimum volume to consider as speech
        self.min_speech_frames = 3    # Minimum consecutive frames to consider speech
    
    def is_speech(self, audio_data: np.ndarray) -> bool:
        """Check if audio contains speech."""
        try:
            if self.use_webrtc and self.vad:
                return self._webrtc_vad(audio_data)
            else:
                return self._simple_vad(audio_data)
                
        except Exception as e:
            logger.error(f"Error in voice activity detection: {e}")
            return False
    
    def _webrtc_vad(self, audio_data: np.ndarray) -> bool:
        """WebRTC VAD implementation."""
        try:
            # Convert to 16-bit PCM
            audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # Process in frames
            speech_frames = 0
            total_frames = 0
            
            for i in range(0, len(audio_int16) - self.frame_size + 1, self.frame_size):
                frame = audio_int16[i:i + self.frame_size]
                
                # WebRTC VAD requires specific sample rates
                if self.sample_rate in [8000, 16000, 32000, 48000]:
                    if self.vad.is_speech(frame.tobytes(), self.sample_rate):
                        speech_frames += 1
                    total_frames += 1
            
            # Consider speech if more than 30% of frames contain speech
            if total_frames > 0:
                speech_ratio = speech_frames / total_frames
                return speech_ratio > 0.3
            
            return False
            
        except Exception as e:
            logger.error(f"Error in WebRTC VAD: {e}")
            # Fallback to simple VAD
            return self._simple_vad(audio_data)
    
    def _simple_vad(self, audio_data: np.ndarray) -> bool:
        """Simple volume-based voice activity detection."""
        try:
            # Calculate RMS (Root Mean Square) energy
            rms = np.sqrt(np.mean(audio_data ** 2))
            
            # Check if volume is above threshold
            if rms > self.volume_threshold:
                return True
            
            # Additional check: look for speech-like patterns
            # Check for variations in amplitude (speech has more variation than noise)
            if len(audio_data) > 100:
                # Calculate standard deviation of amplitude
                std_dev = np.std(audio_data)
                # Speech typically has higher variation than steady noise
                if std_dev > self.volume_threshold * 0.5:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in simple VAD: {e}")
            return False


class VoiceHandler:
    """Main voice input handler."""
    
    def __init__(self):
        self.sample_rate = config.voice.sample_rate
        self.chunk_size = config.voice.chunk_size
        self.silence_threshold = config.voice.silence_threshold
        self.silence_duration = config.voice.silence_duration
        
        # Components
        self.wake_word_detector = WakeWordDetector()
        self.speech_to_text = SpeechToText()
        self.vad = VoiceActivityDetector()
        self.audio_buffer = AudioBuffer(sample_rate=self.sample_rate)
        
        # Audio stream
        self.audio_stream = None
        self.audio_queue = queue.Queue()
        self.recording = False
        self.listening = False
        
        # Threading
        self.audio_thread = None
        self.processing_thread = None
        self.stop_event = threading.Event()
    
    async def initialize(self) -> bool:
        """Initialize voice handler."""
        try:
            logger.info("Initializing voice handler...")
            
            # Initialize components
            if not await self.wake_word_detector.initialize():
                logger.error("Failed to initialize wake word detector")
                return False
            
            if not await self.speech_to_text.initialize():
                logger.error("Failed to initialize speech-to-text")
                return False
            
            # Start audio stream
            self._start_audio_stream()
            
            logger.info("Voice handler initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize voice handler: {e}")
            return False
    
    def _start_audio_stream(self) -> None:
        """Start continuous audio stream."""
        try:
            def audio_callback(indata, frames, time, status):
                if status:
                    logger.warning(f"Audio callback status: {status}")
                
                # Convert to mono if stereo
                if len(indata.shape) > 1:
                    audio_data = np.mean(indata, axis=1)
                else:
                    audio_data = indata.flatten()
                
                # Add to buffer
                self.audio_buffer.write(audio_data)
                
                # Add to queue for processing
                if not self.audio_queue.full():
                    self.audio_queue.put(audio_data.copy())
            
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=self.chunk_size,
                callback=audio_callback
            )
            
            self.audio_stream.start()
            logger.info("Audio stream started")
            
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            raise
    
    async def listen_for_wake_word(self) -> bool:
        """Listen for wake word detection."""
        if not self.wake_word_detector.initialized:
            return False
        
        try:
            # Process audio chunks for wake word detection
            while not self.stop_event.is_set():
                try:
                    # Get audio chunk with timeout
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                    
                    # Detect wake word
                    if self.wake_word_detector.detect(audio_chunk):
                        return True
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing audio for wake word: {e}")
                    await asyncio.sleep(0.1)
            
            return False
            
        except Exception as e:
            logger.error(f"Error in wake word listening: {e}")
            return False
    
    async def record_speech(self, max_duration: float = 10.0) -> Optional[np.ndarray]:
        """Record speech after wake word detection."""
        try:
            logger.debug("Recording speech...")
            
            # Clear the queue
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Record speech
            speech_chunks = []
            silence_start = None
            recording_start = time.time()
            
            while time.time() - recording_start < max_duration:
                try:
                    # Get audio chunk
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                    speech_chunks.append(audio_chunk)
                    
                    # Check for voice activity
                    has_speech = self.vad.is_speech(audio_chunk)
                    
                    if has_speech:
                        silence_start = None
                    else:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > self.silence_duration:
                            # End of speech detected
                            break
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error recording speech: {e}")
                    break
            
            if speech_chunks:
                # Combine chunks
                speech_audio = np.concatenate(speech_chunks)
                logger.debug(f"Recorded {len(speech_audio) / self.sample_rate:.2f} seconds of audio")
                return speech_audio
            
            return None
            
        except Exception as e:
            logger.error(f"Error in speech recording: {e}")
            return None
    
    async def speech_to_text(self, audio_data: np.ndarray) -> Optional[str]:
        """Convert speech audio to text."""
        if not self.speech_to_text.initialized:
            return None
        
        try:
            # Check if audio has sufficient length
            if len(audio_data) < self.sample_rate * 0.5:  # At least 0.5 seconds
                logger.debug("Audio too short for transcription")
                return None
            
            # Transcribe
            text = await self.speech_to_text.transcribe(audio_data)
            return text
            
        except Exception as e:
            logger.error(f"Error in speech-to-text conversion: {e}")
            return None
    
    def cleanup(self) -> None:
        """Cleanup voice handler."""
        logger.info("Cleaning up voice handler...")
        
        # Stop processing
        self.stop_event.set()
        
        # Stop audio stream
        if self.audio_stream:
            try:
                self.audio_stream.stop()
                self.audio_stream.close()
            except:
                pass
            self.audio_stream = None
        
        # Cleanup components
        if self.wake_word_detector:
            self.wake_word_detector.cleanup()
        
        # Clear queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("Voice handler cleanup complete")
