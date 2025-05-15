import os
import re
import logging
import speech_recognition as sr
from pydub import AudioSegment
from word2number import w2n
from colorama import init, Fore, Style
import sounddevice as sd
import soundfile as sf
import tempfile
import wave
import time
import numpy as np

# Initialize logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Initialize colorama
init(autoreset=True)

# Supported audio extensions
AUDIO_EXTS = {'.wav', '.mp3', '.m4a', '.ogg', '.flac'}

# Supported languages
LANGUAGES = {
    'en': 'en-US',
    'ru': 'ru-RU',
    'kk': 'kk-KZ'
}

def check_ffmpeg():
    """Check if FFmpeg is installed to suppress pydub warning."""
    try:
        AudioSegment.from_file(os.devnull, format="mp3")
    except Exception as e:
        logger.warning("FFmpeg not found. Install FFmpeg: `brew install ffmpeg` (macOS).")

def prepare_audio(path: str) -> str:
    """Convert an audio file to WAV if needed; return the WAV path."""
    logger.debug(f"Preparing audio: {path}")
    base, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext == '.wav':
        return path
    if ext in AUDIO_EXTS:
        audio = AudioSegment.from_file(path, format=ext[1:])
        wav_path = f"{base}.wav"
        audio.export(wav_path, format='wav')
        logger.debug(f"Exported WAV: {wav_path}")
        return wav_path
    raise ValueError(f"Unsupported audio format: {ext}")

def list_input_devices():
    """List available input devices with at least one input channel."""
    devices = sd.query_devices()
    input_devices = []
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            input_devices.append((idx, dev['name']))
    return input_devices

def record_to_wav(duration: float, fs: int = 16000, device=None, save_debug=False, gain: float = 2.0) -> str:
    """Record audio with gain adjustment and save to a WAV file."""
    if device is not None:
        sd.default.device = device
        logger.debug(f"sounddevice using device {device}")
    try:
        logger.info(f"Recording {duration}s via sounddevice...")
        data = sd.rec(int(duration * fs), samplerate=fs, channels=1)
        sd.wait()
        # Apply gain to boost audio
        data = data * gain
        # Clip to prevent distortion
        data = np.clip(data, -1.0, 1.0)
        if save_debug:
            debug_path = f"debug_recording_{int(time.time())}.wav"
            sf.write(debug_path, data, fs)
            logger.info(f"Saved debug recording to: {debug_path}")
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, data, fs)
        logger.debug(f"Saved recording to: {tmp.name}")
        return tmp.name
    except Exception as e:
        logger.error(f"Recording failed: {e}")
        raise

def transcribe_file(path: str, language: str = 'en-US', retries: int = 2) -> str:
    """Transcribe an audio file with retries; return text or empty string on failure."""
    wav = prepare_audio(path)
    with wave.open(wav, 'rb') as wf:
        dur = wf.getnframes() / wf.getframerate()
        logger.info(f"File duration: {dur:.2f}s, channels: {wf.getnchannels()}, rate: {wf.getframerate()}Hz")
    rec = sr.Recognizer()
    rec.energy_threshold = 100  # Increased for better noise rejection
    with sr.AudioFile(wav) as source:
        audio_data = rec.record(source)
    for attempt in range(retries):
        try:
            text = rec.recognize_google(audio_data, language=language)
            logger.info(f"File transcription succeeded (attempt {attempt + 1}).")
            return text
        except sr.UnknownValueError:
            logger.warning(f"No speech recognized in file (attempt {attempt + 1}).")
            if attempt < retries - 1:
                logger.info("Retrying transcription...")
                time.sleep(1)
        except sr.RequestError as e:
            logger.error(f"API error: {e}")
            return ""
    return ""

def calibrate_microphone(mic_index: int = None) -> None:
    """Prompt user to test microphone input."""
    print("Testing microphone: Speak for 3 seconds to calibrate (e.g., 'Один два три').")
    try:
        rec = sr.Recognizer()
        rec.energy_threshold = 100
        mic_params = {'device_index': mic_index} if mic_index is not None else {}
        with sr.Microphone(**mic_params) as source:
            logger.info("Calibrating microphone (3s)…")
            rec.adjust_for_ambient_noise(source, duration=1)
            audio_data = rec.record(source, duration=3)
        logger.info("Calibration recording complete.")
        print("Microphone calibration successful. Proceed with recording.")
    except Exception as e:
        logger.error(f"Microphone calibration failed: {e}")
        print("Microphone calibration failed. Check device settings and permissions.")

def transcribe_mic(duration: int = 5, language: str = 'en-US', mic_index: int = None, save_debug=False) -> str:
    """Transcribe microphone input with fallback to sounddevice."""
    try:
        rec = sr.Recognizer()
        rec.energy_threshold = 100  # Increased for better noise rejection
        mic_params = {'device_index': mic_index} if mic_index is not None else {}
        with sr.Microphone(**mic_params) as source:
            logger.info("Adjusting for ambient noise (1s)…")
            rec.adjust_for_ambient_noise(source, duration=1)
            logger.debug(f"Energy threshold: {rec.energy_threshold}")
            logger.info(f"Recording speech for {duration}s...")
            audio_data = rec.record(source, duration=duration)
        text = rec.recognize_google(audio_data, language=language)
        logger.info("Mic transcription succeeded via speech_recognition.")
        return text
    except Exception as e:
        logger.warning(f"speech_recognition Mic failed: {e}. Falling back to sounddevice.")
        wav = record_to_wav(duration, device=mic_index, save_debug=save_debug)
        try:
            text = transcribe_file(wav, language)
            return text
        finally:
            if not save_debug:
                try:
                    os.remove(wav)
                    logger.debug(f"Cleaned up temporary file: {wav}")
                except Exception:
                    logger.warning(f"Failed to delete temporary file: {wav}")

def replace_number_words(text: str, language: str = 'en') -> str:
    """Convert spelled-out numbers to digits (English only)."""
    logger.debug(f"Converting number words in: '{text}'")
    if language != 'en':
        logger.info(f"Number word conversion skipped for language: {language}")
        return text
    tokens = re.findall(r"\w+|[^\w\s]", text)
    i, out = 0, []
    while i < len(tokens):
        if re.fullmatch(r"\w+", tokens[i]):
            for j in range(len(tokens), i, -1):
                phrase = ' '.join(tokens[i:j]).lower()
                try:
                    num = w2n.word_to_num(phrase)
                    logger.debug(f"'{phrase}'→{num}")
                    out.append(str(num))
                    i = j
                    break
                except ValueError:
                    continue
            else:
                out.append(tokens[i])
                i += 1
        else:
            out.append(tokens[i])
            i += 1
    result = ''.join(t if re.fullmatch(r"[^\w]", t) else t + ' ' for t in out).strip()
    logger.debug(f"After conversion: '{result}'")
    return result

def highlight_numbers(text: str) -> str:
    """Highlight numeric digits in text."""
    def hl(m):
        n = m.group(0)
        logger.debug(f"Highlighting: {n}")
        return f"{Fore.YELLOW}{n}{Style.RESET_ALL}"
    return re.sub(r"\b\d+\b", hl, text)

def run():
    logger.info("Starting program…")
    check_ffmpeg()
    print("1) Audio File\n2) Microphone")
    choice = input("Enter 1 or 2: ").strip()
    lang_code = input("Language (en for English, ru for Russian, kk for Kazakh, default en): ").strip().lower() or 'en'
    language = LANGUAGES.get(lang_code, 'en-US')
    print(f"Using language: {language}")

    mic_index = None
    duration = 5
    save_debug = False
    max_attempts = 2
    attempt = 1

    if choice == '2':
        input_devices = list_input_devices()
        if not input_devices:
            print("No input devices found. Exiting.")
            return
        print("Available input devices:")
        for idx, name in input_devices:
            print(f" {idx}: {name}")
        sel = input("Select device index (blank=default): ").strip()
        if sel.isdigit() and any(idx == int(sel) for idx, _ in input_devices):
            mic_index = int(sel)
        dur = input("Duration in seconds (blank=5s): ").strip()
        duration = int(dur) if dur.isdigit() else 5
        debug_input = input("Save debug WAV file? (y/n, default n): ").strip().lower()
        save_debug = debug_input == 'y'
        calibrate_microphone(mic_index)

    while attempt <= max_attempts:
        print(f"\nRecording attempt {attempt} of {max_attempts}...")
        if choice == '1':
            path = input("Audio file path: ").strip()
            if not os.path.exists(path):
                print("File not found.")
                return
            text = transcribe_file(path, language)
        elif choice == '2':
            text = transcribe_mic(duration=duration, language=language, mic_index=mic_index, save_debug=save_debug)
        else:
            print("Invalid choice.")
            return

        if text:
            break
        print("No transcription. Check debug WAV file or microphone settings.")
        if attempt < max_attempts:
            print("Retrying...")
            time.sleep(2)
        attempt += 1

    if not text:
        print("All attempts failed. Please try again or use a different microphone.")
        return

    converted = replace_number_words(text, lang_code)
    highlighted = highlight_numbers(converted)

    # Save to output.txt
    out_path = 'output.txt'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(highlighted)
    logger.info(f"Saved highlighted transcription to {out_path}")

    print(f"Transcription with highlights written to {out_path}")
    print("Transcription:", highlighted)

if __name__ == '__main__':
    run()