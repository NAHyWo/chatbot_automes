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

from tempfile import NamedTemporaryFile
from fastapi import UploadFile
import whisper

# Whisper 모델 로드
model = whisper.load_model('turbo')  # 또는 'small', 'medium', 'large', 'turbo' 등


async def speech_to_text_from_file() -> str:
    file_path = os.path.join(voice_dir, "input.wav")
    if not os.path.exists(file_path):
        raise FileNotFoundError("지정된 파일이 존재하지 않습니다.")

    if not file_path.lower().endswith((".wav", ".mp3", ".m4a", ".flac")):
        raise ValueError("지원하지 않는 오디오 형식입니다.")

    # Whisper로 STT 수행
    stt_result = model.transcribe(file_path, language="ko")
    user_text = stt_result.get("text", "").strip()

    if not user_text:
        raise ValueError("음성 인식에 실패했습니다.")

    return user_text
