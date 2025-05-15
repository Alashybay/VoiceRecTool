# Voice Input Number Highlighter

A beginner-friendly Python tool that lets you record or load audio and convert spoken words into text, automatically turning spelled‑out numbers into digits and highlighting them.

---

## 📋 Overview

* **Record** from your microphone or **load** an audio file (WAV, MP3, M4A, OGG, FLAC).
* **Transcribe** speech to text using Google’s free Web Speech API (no key required).
* **Convert** number words ("one hundred twenty three") into digits (`123`).
* **Highlight** all digits in the output.
* **Save** the final result to `output.txt`.

## 🚀 Getting Started

### Prerequisites

1. **Python 3.7+** installed on your computer.
2. **FFmpeg** (for audio file support):

   * **macOS**: `brew install ffmpeg`
   * **Windows/Linux**: download from [ffmpeg.org](https://ffmpeg.org/) and add to your PATH.

### Install Required Python Packages

Open a terminal (Command Prompt, PowerShell, or macOS Terminal) and run:

```bash
pip install SpeechRecognition pydub word2number colorama sounddevice soundfile
```

## ⚙️ How to Use

1. **Open a terminal** in the folder where the `speech_to_numbers.py` script lives.
2. **Run the script**:

   ```bash
   python speech_to_numbers.py
   ```
3. **Follow on-screen prompts**:

   * **Choose input**: `1` for an audio file, or `2` for microphone.
   * **Language code**: enter `en-US`, `ru-RU`, or `kk-KZ` (default is `en-US`).
   * If you select **microphone**:

     1. The tool will **list** all available input devices.
     2. Enter the **index** of your preferred mic (or leave blank to use the default).
     3. Specify **recording duration** in seconds (default is 5s).
     4. (Optional) **Calibrate** the mic by speaking a short phrase (e.g. "one two three").
4. **Wait** for the recording/transcription to finish.
5. **Open** the generated `output.txt` file to see your transcribed text with numbers highlighted.

## 📂 Output

* **output.txt** — Contains the final text with:

  * Numbers converted to digits.
  * Digits highlighted in the console and in the saved file.

Example line in `output.txt`:

```
I have 2 apples and 15 oranges.
```

## 🛠️ How It Works (Brief Report)

1. **Initialization**: loads libraries and configures logging for debug messages.
2. **Input selection**:

   * **Audio file**: converts non‑WAV formats to WAV via FFmpeg + pydub.
   * **Microphone**: attempts to use PyAudio (via `speech_recognition`); if unavailable, falls back to pure-Python `sounddevice`.
3. **Transcription**:

   * Uses Google’s free Web Speech API for speech‑to‑text.
   * Retries on failure (for file input) and logs errors for troubleshooting.
4. **Number conversion**: scans the text for spelled‑out number sequences, converts them to numeric digits.
5. **Highlighting**: wraps all digit sequences in ANSI color codes (yellow) via `colorama`.
6. **Saving**: writes the final highlighted text to `output.txt` in the current directory.

## 🔧 Troubleshooting Tips

* **No transcription**:

  * Check your microphone permissions.
  * Try a different input device index.
  * Use the `debug_recording_*.wav` (if enabled) to inspect what was recorded.
* **FFmpeg warnings**: install FFmpeg to avoid pydub warnings and ensure file conversion.
* **Language issues**: ensure you enter a valid language code from the supported list.

---

Feel free to customize recording duration, language support, or add other file formats. Enjoy turning speech into text with highlighted numbers!
