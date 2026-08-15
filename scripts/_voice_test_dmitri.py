"""One-off: synthesize the test phrase through the real PiperTTS code path
(voice selection by language + anti-override tuning logic) and verify the
WAV is produced with no error and a sane size/duration."""
import sys, wave, subprocess
from pathlib import Path

ROOT = Path(r"E:\jarvis-project")
sys.path.insert(0, str(ROOT))

from config import load_config
from core.voice import PiperTTS

settings = load_config()
tts = PiperTTS(settings)
print("available:", tts.is_available())
print("voices:", tts.available_voices)

text = "Здравствуйте, сэр. Система готова к работе."
voice = tts._select_voice(text)
print("selected voice:", voice.name, "| lang:", voice.language)

has_tuning = (voice.noise_scale > 0) or (voice.noise_w > 0) or (voice.length_scale != 1.0)
print(f"anti-override tuning active (use_model_tuning): {has_tuning} "
      f"noise_scale={voice.noise_scale} noise_w={voice.noise_w} length_scale={voice.length_scale}")

out = ROOT / "data" / "models" / "piper" / "_voice_test_dmitri.wav"
cmd = [str(tts._binary), "--model", str(voice.model_path),
       "--speaker", str(voice.speaker_id), "--output_file", str(out)]
if has_tuning:
    cmd += ["--length_scale", str(voice.length_scale),
            "--noise_scale", str(voice.noise_scale),
            "--noise_w", str(voice.noise_w)]

proc = subprocess.run(cmd, input=text.strip().encode("utf-8"),
                      capture_output=True, timeout=30)
print("returncode:", proc.returncode)
if proc.stderr:
    print("stderr:", proc.stderr.decode(errors="ignore")[:600])

print("wav exists:", out.exists(), "| size:", out.stat().st_size if out.exists() else 0)
if out.exists():
    with wave.open(str(out)) as wf:
        dur = wf.getnframes() / float(wf.getframerate())
        print(f"duration: {dur:.2f}s | rate: {wf.getframerate()} | channels: {wf.getnchannels()}")
    out.unlink()
print("VOICE TEST DONE")
