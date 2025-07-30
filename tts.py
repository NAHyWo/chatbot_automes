import os

# 기본 디렉토리 설정
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, "data")
voice_dir = os.path.join(base_dir, "voice")
os.environ["HF_HOME"] = os.path.join(base_dir, "huggingface_cache")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "transformers")
os.environ["HF_HUB_CACHE"] = os.path.join(base_dir, "huggingface_cache", "hub")
os.environ["HF_DATASETS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "datasets")
os.environ["TORCH_HOME"] = os.path.join(base_dir, "huggingface_cache", "torch")
os.environ["TMPDIR"] = os.path.join(base_dir, "huggingface_cache", "tmp")

import torchaudio
from chatterbox.tts import ChatterboxTTS

model = ChatterboxTTS.from_pretrained(device="cuda")


def text_to_speech(text: str):
    if not text.strip():
        raise ValueError("텍스트를 입력하세요.")

    wav = model.generate(text)

    os.makedirs(voice_dir, exist_ok=True)

    output_path = os.path.join(voice_dir, 'temp.wav')
    torchaudio.save(output_path, wav, model.sr)

    return output_path
