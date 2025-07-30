import os
import sys

# 현재 파일 기준으로 경로 설정 (LLM 모델 저장 위치)
base_dir = os.path.abspath(os.path.dirname(__file__))
os.environ["HF_HOME"] = os.path.join(base_dir, "huggingface_cache")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "transformers")
os.environ["HF_HUB_CACHE"] = os.path.join(base_dir, "huggingface_cache", "hub")
os.environ["HF_DATASETS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "datasets")
os.environ["TORCH_HOME"] = os.path.join(base_dir, "huggingface_cache", "torch")
os.environ["TMPDIR"] = os.path.join(base_dir, "huggingface_cache", "tmp")

# RAG 결과 FAISS 인덱스 및 관련 파일 로드
index_path = os.path.join("rag", "my_index.faiss")
texts_path = os.path.join("rag", "my_index_texts.pkl")
sources_path = os.path.join("rag", "my_index_sources.pkl")
embeddings_path = os.path.join("rag", "my_index_embeddings.npy")

import torch
import re
import json
import pickle
import faiss
import numpy as np
import pandas as pd
import pymysql
import datetime

# 허깅페이스 모델 및 프롬프트 템플릿 관련 모듈
from huggingface_hub.utils import is_fastai_available
from transformers import MllamaForConditionalGeneration, MllamaProcessor, AutoModelForCausalLM, AutoTokenizer
from sentence_transformers import SentenceTransformer

# ------------------- 자체 모듈 함수 -------------------
from config import config
from prompts import (
    SQL_SYSTEM_MSG, SQL_RESPONSE_SYSTEM_MSG, FUNCTION_SYSTEM_MSG, FUNCTION_SQL_SYSTEM_MSG, RAG_SYSTEM_MSG,
    NLG_SYSTEM_MSG, NLG_USER_TEMPLATE, DETERMINATION_PROMPT, GENERAL_SYSTEM_MSG, DB_SCHEMA
)
from function import (general_impl, query_impl)
from utils.json_encoder import JSONEncoder

# 히스토리 파일 관련 위치 및 제한 설정
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "chat_history.json")
HISTORY_FILE = os.path.normpath(HISTORY_FILE)
MAX_HISTORY = 10

# RAG 관련 데이터 로드
rag_index = faiss.read_index(index_path)
with open(texts_path, "rb") as f:
    rag_texts = pickle.load(f)
with open(sources_path, "rb") as f:
    rag_sources = pickle.load(f)
embeddings = np.load(embeddings_path)
# L2 정규화 (벡터 길이 1로 맞추기): FAISS 검색 정확도 향상
embeddings_normalized = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

# Bllossom: 한국어 LLaMA 모델 (일반 대화용)
bllossom_model = MllamaForConditionalGeneration.from_pretrained(
    "Bllossom/llama-3.2-Korean-Bllossom-AICA-5B",
    local_files_only=True,
    torch_dtype=torch.float32,
    device_map=None).to('cpu')
bllossom_processor = MllamaProcessor.from_pretrained("Bllossom/llama-3.2-Korean-Bllossom-AICA-5B", local_files_only=True)

# BAAI: 문서 임베딩 모델 (RAG용)
baai_model = SentenceTransformer("BAAI/bge-m3", local_files_only=True)

# defog: SQL 생성 전용 모델 (현재 하드웨어 성능상 사용 어려움, 주석 처리)
"""
defog_model = AutoModelForCausalLM.from_pretrained(
    "defog/llama-3-sqlcoder-8b", 
    local_files_only=True, 
    torch_dtype=torch.float32, 
    device_map=None).to('cpu')
defog_tokenizer = AutoTokenizer.from_pretrained("defog/llama-3-sqlcoder-8b", local_files_only=True)
"""

# LoRA 어댑터 캐시
lora_adapters_cache = {}

# 모델 및 프로세서 로딩
MODELS = {
    "bllossom": {
        "base": bllossom_model,
        "model": bllossom_model,
        "processor": bllossom_processor
    },
    "BAAI": {
        "model": baai_model
    },
    #"defog": {
    #    "model": defog_model,
    #    "tokenizer": defog_tokenizer
    #}
}

# MySQL DB 연결
def get_connection():
    return pymysql.connect(
        host=config.DB_HOST,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        port=config.DB_PORT,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# 저장된 대화 히스토리를 불러오는 함수
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
            if isinstance(history, list):
                return history
    return []

# 히스토리에 대화 저장
def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)

# 히스토리 내역 삭제
def clear_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return {"status": "success", "message": "Chat history cleared."}
    except Exception as e:
        raise e

# LoRA 어댑터를 모델에 로드하고 캐싱
def lora_load(adapter_name, adapter_path):
    if adapter_name not in lora_adapters_cache:
        print(f"Loading LoRA adapter {adapter_name}...")
        bllossom_model.load_adapter(adapter_path, adapter_name=adapter_name)
        lora_adapters_cache[adapter_name] = bllossom_model.get_adapter(adapter_name)
    else:
        print(f"LoRA adapter {adapter_name} already cached.")

# LoRA 어댑터 적용 또는 제거 (None이면 제거)
def lora_apply(adapter_name=None):
    if adapter_name is None:
        print("Removing LoRA adapter, switching to base model.")
        bllossom_model.reset_adapter()
        MODELS["bllossom"]["model"] = bllossom_model
    else:
        if adapter_name in lora_adapters_cache:
            print(f"Applying LoRA adapter {adapter_name}.")
            bllossom_model.set_adapter(adapter_name)
            bllossom_model.apply_adapter(adapter_name)
            MODELS["bllossom"]["model"] = bllossom_model
        else:
            raise ValueError(f"LoRA adapter '{adapter_name}' not loaded.")

# LoRA 어댑터 로딩
#lora_load("determine", "./lora/determine")

# Function Calling 용 문자열 내 JSON 추출 (파싱 실패 시 None)
def try_parse_json(s):
    if not isinstance(s, str):
        return None
    try:
        # JSON 시작과 끝을 포함하는 가장 바깥 괄호 찾기
        match = re.search(r'\{[\s\S]*\}', s)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
    except json.JSONDecodeError:
        return None
    return None

# defog 모델 전용 프롬프트 생성 함수 (현재 사용 안함)
def convert_sqlcoder_prompt(messages):
    #messages = [msg["content"] for msg in messages if msg["role"] == "user"]
    if not messages:
        return "<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\nNo question provided.<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"

    #question = messages[-1]
    question = messages

    prompt = (
        f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n"
        f"Generate a MySQL query to answer this question: `{question}`\n"
        f"\nDDL statements:\n{DB_SCHEMA}"
        f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        f"The following SQL query best answers the question `{question}`:\n```sql\n"
    )
    return prompt


# 출력문 assistant 다음 부분만 추출 (없을 시 LLM이 대화 생성한 내용 모두 출력함)
def extract_assistant_response(message):
    split_pattern = r"assistant\s*\n"    # 'assistant\n' 뒤의 텍스트가 마지막 응답
    parts = re.split(split_pattern, message)
    if len(parts) > 1:
        return parts[-1].strip()
    return message.strip()

# Query 출력문 ```sql``` 제거 추출
def extract_query_response(message):
    pattern_triplequote = r"'''sql\s*(.*?)\s*'''"
    pattern_backtick = r"```sql\s*(.*?)\s*```"
    for pattern in [pattern_triplequote, pattern_backtick]:
        match = re.search(pattern, message, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return message.strip()



# 로컬 LLM 모델 호출 함수 (호출 모델 별 프롬프트 구성 및 처리)
def llm_calling(messages, max_new_tokens, temperature, model_name="bllossom", eos_token="<|eot_id|>"):
    model_info = MODELS[model_name]
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # 오늘 날짜 삽입
    messages.insert(-1, {"role": "system", "content": f"오늘은 {today}입니다."})

    # defog 모델 사용 (현재는 사용 불가)
    if model_name == "defog":
        # defog/sqlcoder는 chat_template이 없기 때문에 수동 프롬프트 구성
        model = model_info["model"]
        prompt = convert_sqlcoder_prompt(messages)
        tokenizer = model_info["tokenizer"]
        inputs = tokenizer(prompt, return_tensors="pt").to('cpu')

        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            eos_token_id=tokenizer.eos_token_id
        )

        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    # default 모델은 Bllossom
    else:
        model = model_info["model"]
        processor = model_info["processor"]
        input_text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = processor(text=input_text, return_tensors="pt").to('cpu')

        output = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            eos_token_id=processor.tokenizer.convert_tokens_to_ids(eos_token),
            use_cache=True
        )

        raw_output = processor.decode(output[0], skip_special_tokens=True)
        clean_output = extract_assistant_response(raw_output)
        return clean_output

# 질문이 원하는 실행 유형 판단 (SQL Query, Function Call, RAG Response, General Response)
def determine_mode_response(message, history=None):
    #lora_apply("determine") # LoRA 어댑터 있을 시 적용 가능
    messages = history[-MAX_HISTORY:] if history else [] # 최근 MAX_HISTORY 값 만큼 히스토리 내역 추가
    messages.append({"role": "system", "content": DETERMINATION_PROMPT}) # 필요에 따라 적절한 프롬프트 추가
    messages.append({"role": "user", "content": message}) # 질문 추가
    return llm_calling(messages, 16, 0.1, "bllossom") # llm_calling 함수 실행 후 결과 문자열 반환

# Function calling 용 JSON 생성, 현재 DB값 선, 막대, 원 그래프로 그려주는 시각화 함수 구현
def generate_function_call(message, history=None):
    #lora_apply("none")
    messages = history[-MAX_HISTORY:] if history else []
    messages.append({"role": "system", "content": FUNCTION_SYSTEM_MSG})
    messages.append({"role": "user", "content": message})
    return llm_calling(messages, 512, 0.1, "bllossom")

# 입력할 data가 DB에서 조회해야하는 경우 SQL Query 생성
def generate_function_sql_response(message, history=None):
    # lora_apply("none")
    messages = history[-MAX_HISTORY:] if history else []
    messages.append({"role": "system", "content": FUNCTION_SQL_SYSTEM_MSG})
    messages.append({"role": "user", "content": message})
    return llm_calling(messages, 128, 0.1, "bllossom")
    #return llm_calling(message, 128, 0.1, "defog") # 하드웨어 여건될 시 defog 모델 사용

# 일반 대화 응답 생성
def generate_general_response(message, history=None):
    # lora_apply("none")
    messages = history[-MAX_HISTORY:] if history else []
    messages.append({"role": "system", "content": GENERAL_SYSTEM_MSG})
    messages.append({"role": "user", "content": message})
    return llm_calling(messages, 128, 0.3, "bllossom")

# DB 조회 용 Query 생성
def generate_sql_query(message, history=None):
    # lora_apply("none")
    messages = history[-MAX_HISTORY:] if history else []
    messages.append({"role": "system", "content": SQL_SYSTEM_MSG})
    messages.append({"role": "user", "content": message})
    return llm_calling(messages, 128, 0.1, "bllossom")
    #return llm_calling(message, 128, 0.1, "defog") # 하드웨어 여건될 시 defog 모델 사용

# 생성된 Query로 DB 조회 및 응답 생성
def generate_sql_response(message, history=None):
    sql_query = extract_query_response(generate_sql_query(message, history))
    try:
        # DB 연결 및 SQL 실행
        conn = get_connection()
        cursor = conn.cursor()
        results = []
        queries = [q.strip() for q in sql_query.split(';') if q.strip()]
        for q in queries:
            cursor.execute(q)
            results.append(cursor.fetchall())
        cursor.close()
        conn.close()
        print(results)
    except Exception as e:
        return 'DB 조회 중 오류 발생'

    # lora_apply("none")
    user_prompt = f"사용자 질문: {message}\nDB 조회 결과:\n{results}\n\n위 결과를 바탕으로 사용자 질문에 대해 자연어로 대답해줘."
    messages = history[-MAX_HISTORY:] if history else []
    messages.append({"role": "system", "content": SQL_RESPONSE_SYSTEM_MSG})
    messages.append({"role": "user", "content": [{"type": "text", "text": user_prompt}]})
    return llm_calling(messages, 256, 0.1, "bllossom")

# Function calling 실패 시 적절한 응답 생성
def generate_nlg_response(question, function, query=None, result=None, history=None):
    # lora_apply("none")
    messages = history[-MAX_HISTORY:] if history else []
    messages.append({"role": "system", "content": NLG_SYSTEM_MSG}) # System 프롬프트 설정
    user_msg = NLG_USER_TEMPLATE.format(question=question, json=function, query=query, data=json.dumps(result, ensure_ascii=False, cls=JSONEncoder)) # User 메시지 구성: 질문과 데이터 포함
    messages.append({"role": "user", "content": user_msg})
    return llm_calling(messages, 256, 0.3, "bllossom")

# 유사도 기반 문서 검색 + 응답 생성
def generate_rag_response(message, history=None):
    # lora_apply("none")
    # 1. Query embedding
    query_embedding = MODELS["BAAI"]["model"].encode([message])
    # 2. FAISS 검색
    top_k = 3
    distances, indices = rag_index.search(query_embedding, top_k)
    # 3. 거리 필터링
    distance_threshold = 8.0  # 원하는 최대 거리
    filtered = [
        (idx, dist)
        for idx, dist in zip(indices[0], distances[0])
        if dist <= distance_threshold
    ]
    if not filtered:
        user_prompt = (
            f"참고할 문서가 없습니다.\n"
            f"[질문]\n{message}"
        )
    else:
        # 4. 검색된 문서 추출 및 정리
        retrieved_docs = [rag_texts[idx] for idx in indices[0]]
        context_text = "\n\n".join([
            f"[{rag_sources[idx]}] (L2 거리: {dist:.4f})\n{rag_texts[idx]}"
            for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]))
        ])
        # 5. 프롬프트 구성
        user_prompt = (
            f"다음 문서를 참고하여 질문에 답하십시오.\n\n"
            f"{context_text}\n\n"
            f"[질문]\n{message}"
        )
    messages = history[-MAX_HISTORY:] if history else []
    messages.append({"role": "system", "content": RAG_SYSTEM_MSG})
    messages.append({"role": "user", "content": [{"type": "text", "text": user_prompt}]})
    # 6. LLM 호출
    llm_response = llm_calling(messages, 1024, 0.2, "bllossom")
    return f"{user_prompt}\n\n---\n\n{llm_response}"


def determine_response(message, mode=None):
    """
    사용자의 질문에 대해 적절한 응답을 판단하여 반환

    - mode == None: 자동 분류 (LLM 활용)
    - Function Call, SQL, RAG 분기 처리
    """
    history = load_history()
    history.append({"role": "user", "content": message})

    if mode is None:
        response_mode = determine_mode_response(message, history)
        print(response_mode)
    else:
        response_mode = mode

    if "Function Call" in response_mode:
        testre = generate_function_call(message, history)
        parsed = try_parse_json(testre)
        if  parsed and "function" in parsed:
            function_name = parsed["function"]
            if "arguments" in parsed and parsed["arguments"]["data"]:
                arguments = parsed["arguments"]
                try:
                    fn = getattr(general_impl, function_name)

                    # JSON 구조에 맞게 arguments 안의 "data"와 나머지 항목들을 분리
                    data_args = arguments.get("data", {})
                    other_args = {k: v for k, v in arguments.items() if k != "data"}

                    # 두 딕셔너리를 병합하여 함수 인자로 전달
                    fn_args = {"data": data_args, **other_args}
                    raw_result = fn(**fn_args)

                    if isinstance(raw_result, str) and os.path.isfile(raw_result):
                        print(raw_result)
                        history.append({"role": "assistant", "content": raw_result})
                        save_history(history)
                        formatted_path = raw_result.replace('\\', '/')
                        return f'[image]{formatted_path}'
                    else:
                        nlg_resp = generate_nlg_response(message, parsed, None, raw_result, history)
                        print(nlg_resp)
                        history.append({"role": "assistant", "content": nlg_resp})
                        save_history(history)
                        return nlg_resp
                except Exception as e:
                    print(f"함수 실행 중 오류 발생: {e}")
                    history.append({"role": "assistant", "content": f"함수 실행 중 오류 발생: {e}"})
                    save_history(history)
                    return f"함수 실행 중 오류 발생: {e}"
            # DB에서 data를 조회하는 경우 생성된 JSON의 data가 비어있음
            elif "arguments" in parsed and not parsed["arguments"]["data"]:
                try:
                    fn = getattr(query_impl, function_name)
                    query = extract_query_response(generate_function_sql_response(message, history))
                    raw_result = fn(query)
                    if isinstance(raw_result, str) and os.path.isfile(raw_result):
                        print(raw_result)
                        history.append({"role": "assistant", "content": raw_result})
                        save_history(history)
                        formatted_path = raw_result.replace('\\', '/')
                        return f'[image]{formatted_path}'
                    else:
                        nlg_resp = generate_nlg_response(message, parsed, query, raw_result, history)
                        print(nlg_resp)
                        history.append({"role": "assistant", "content": nlg_resp})
                        save_history(history)
                        return nlg_resp
                except Exception as e:
                    print(f"SQL 처리 중 오류 발생: {e}")
                    history.append({"role": "assistant", "content": f"SQL 처리 중 오류 발생: {e}"})
                    return f"SQL 처리 중 오류 발생: {e}"
            else:
                print(f"입력 Data 오류 발생: {parsed}")
                history.append({"role": "assistant", "content": f"입력 Data 오류 발생: {parsed}"})
                save_history(history)
                return f"입력 Data 오류 발생: {parsed}"
        else:
            print("정의되지 않은 함수입니다.")
            history.append({"role": "assistant", "content": "정의되지 않은 함수입니다."})
            save_history(history)
            return "정의되지 않은 함수입니다."

    elif "SQL Query" in response_mode:
        try:
            result = generate_sql_response(message, history)
            #result = extract_query_response(generate_sql_query(message, history))
            print(result)
            history.append({"role": "assistant", "content": result})
            save_history(history)
            return result

        except Exception as e:
            print(f"SQL 처리 중 오류 발생: {e}")
            history.append({"role": "assistant", "content": f"SQL 처리 중 오류 발생: {e}"})
            return f"SQL 처리 중 오류 발생: {e}"

    elif "Rag Response" in response_mode:
        result = generate_rag_response(message)
        print(result)
        history.append({"role": "assistant", "content": result})
        save_history(history)
        return result

    else:
        result = generate_general_response(message)
        print(result)
        history.append({"role": "assistant", "content": result})
        save_history(history)
        return result


def run_chat():
    while True:
        message = input("질문하세요 (종료: exit): ")
        if message.strip().lower() == "exit":
            break
        determine_response(message)
