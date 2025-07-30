import os

# 현재 파일 기준으로 절대 경로 설정
base_dir = os.path.abspath(os.path.dirname(__file__))
data_dir = os.path.join(base_dir, "data")
os.environ["TORCH_HOME"] =  os.path.join(base_dir, "torch_cache")

# ------------------- 외부 패키지 -------------------
import uvicorn
from typing import Optional
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ------------------- 자체 모듈 함수 -------------------
from chatbot import determine_response, clear_history
# STT, TTS 관련 모듈은 현재 주석 처리
#from stt import speach_to_text
#from tts import text_to_speach


# ------------------- FastAPI 앱 초기화 및 라우팅 -------------------
app = FastAPI() # FastAPI 앱 객체 생성
app.mount("/static", StaticFiles(directory=data_dir), name="static")


# 채팅 요청 JSON 형식 정의
class ChatRequest(BaseModel):
    message: str                # 사용자가 입력한 메시지
    mode: Optional[str] = None  # 선택적으로 전달 가능한 응답 모드


# ------------------- 라우트 정의 -------------------
# 채팅 처리 API
@app.post("/chat")
def chat(request: ChatRequest):
    """
    사용자의 채팅 메시지를 받아 응답을 생성하는 API.
    - 입력: {"message": "안녕", "mode": "SQL Query"}
    - 출력: {"message": "DB 조회 결과 출력"}
    """
    try:
        # chatbot.py의 함수 호출하여 응답 생성
        response_text = determine_response(request.message, mode=request.mode)
        if response_text.startswith("[image]"):
            # 원본 경로 추출
            local_path = response_text[len("[image]"):].strip()
            # 파일 이름 추출 (예: D:/data/cat.png -> cat.png)
            filename = os.path.basename(local_path)
            return {"message": f"[image]{filename}"}
        return {"message": response_text}
    except Exception as e:
        # 오류 발생 시 에러 메시지 반환
        return {"error": str(e)}

# 음성 → 텍스트 변환 API (비활성화)
"""
@app.post("/stt")
async def stt(file: UploadFile = File(...)):
    '''
    업로드된 음성 파일을 텍스트로 변환하는 API.
    - 입력: 오디오 파일 (.wav 등)
    - 출력: {"text": "인식된 텍스트"}
    '''
    try:
        user_text = await speach_to_text(file)
        return JSONResponse({"text": user_text})
    except ValueError as ve:
        return PlainTextResponse(str(ve), status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
"""

# 텍스트 → 음성 변환 API (비활성화)
"""
@app.post("/tts")
async def tts(message: str = Form(...)):
    '''
    입력된 텍스트를 음성으로 변환하고, 해당 음성 파일 경로를 반환하는 API.
    - 입력: {"message": "안녕하세요"}
    - 출력: {"text": "static/output.wav"}
    '''
    try:
        wav_path = text_to_speech(message)
        return JSONResponse({"text": wav_path})
    except ValueError as ve:
        return PlainTextResponse(str(ve), status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
"""

# 채팅 기록 초기화 API
@app.post("/clear")
def clear():
    """
    대화 기록을 초기화하는 API.
    - 호출 시 chatbot.py 내 clear_history() 함수를 실행.
    - 출력: 초기화 진행 또는 에러 메시지
    """
    try:
        return clear_history()  # chatbot.py의 함수 호출
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=443,
        ssl_keyfile="-key.pem",
        ssl_certfile=".pem"
    )
