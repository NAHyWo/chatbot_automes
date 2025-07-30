import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.abspath(os.path.join(current_dir, ".."))

os.environ["HF_HOME"] = os.path.join(base_dir, "huggingface_cache")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "transformers")
os.environ["HF_HUB_CACHE"] = os.path.join(base_dir, "huggingface_cache", "hub")
os.environ["HF_DATASETS_CACHE"] = os.path.join(base_dir, "huggingface_cache", "datasets")
os.environ["TORCH_HOME"] = os.path.join(base_dir, "huggingface_cache", "torch")
os.environ["TMPDIR"] = os.path.join(base_dir, "huggingface_cache", "tmp")

import time
import torch
from transformers import (
    MllamaForConditionalGeneration,
    MllamaProcessor,
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    default_data_collator,
    TrainerCallback
)
from peft import LoraConfig, get_peft_model, TaskType, PeftModel
from datasets import load_dataset


model_name = "Bllossom/llama-3.2-Korean-Bllossom-AICA-5B"

# 간단한 남은 시간 출력 콜백 추가
class TimeEstimatorCallback(TrainerCallback):
    def __init__(self):
        self.start_time = None

    def on_train_begin(self, args, state, control, **kwargs):
        self.start_time = time.time()

    def on_step_end(self, args, state, control, **kwargs):
        elapsed = time.time() - self.start_time
        steps_done = state.global_step
        total_steps = state.max_steps

        if steps_done > 0 and total_steps > 0:
            time_per_step = elapsed / steps_done
            remaining_steps = total_steps - steps_done
            eta = remaining_steps * time_per_step
            eta_min, eta_sec = divmod(int(eta), 60)
            print(f"[Step {steps_done}/{total_steps}] 남은 시간 약 {eta_min}분 {eta_sec}초")

def train_lora(json_path, output_folder):
    print(f"=== {os.path.basename(json_path)} 학습 시작 ===")

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="auto",
        load_in_8bit=True,
        local_files_only=True
    )
    tokenizer = AutoTokenizer.from_pretrained(model_name, local_files_only=True)
    tokenizer.padding_side = "right"
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.pad_token_id = tokenizer.eos_token_id

    lora_config = LoraConfig(
        r=8,
        lora_alpha=16,
        target_modules=["q_proj", "v_proj"],
        lora_dropout=0.1,
        bias="none",
        task_type=TaskType.CAUSAL_LM
    )
    model = get_peft_model(model, lora_config)

    dataset = load_dataset("json", data_files={"train": json_path})
    dataset = dataset["train"].train_test_split(test_size=0.1)

    def preprocess(example):
        inputs = tokenizer(
            example["input"],
            truncation=True,
            max_length=512,
            padding="max_length"
        )
        labels = tokenizer(
            example["output"],
            truncation=True,
            max_length=512,
            padding="max_length"
        )["input_ids"]
        inputs["labels"] = labels
        return inputs

    tokenized_dataset = dataset.map(preprocess, batched=True, remove_columns=dataset["train"].column_names)

    os.makedirs(output_folder, exist_ok=True)
    log_dir = os.path.join(current_dir, "logs", os.path.basename(output_folder))
    os.makedirs(log_dir, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=output_folder,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        num_train_epochs=3,
        logging_dir=log_dir,
        logging_steps=10,
        fp16=True,
        report_to="none",
        save_total_limit=2
        # 'evaluation_strategy'와 'save_strategy' 제거
    )

    data_collator = default_data_collator

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["test"],
        tokenizer=tokenizer,
        data_collator=data_collator,
        callbacks=[TimeEstimatorCallback()]  # 여기서 콜백 추가
    )

    trainer.train()

    if isinstance(model, PeftModel):
        model.save_pretrained(output_folder, safe_serialization=True)
        print(f"LoRA 어댑터 '{output_folder}'에 저장 완료")
    else:
        print(f"모델이 PeftModel 타입이 아니므로 어댑터 저장 실패")

    tokenizer.save_pretrained(output_folder)
    print(f"토크나이저 '{output_folder}'에 저장 완료\n")

jsonl_files = [f for f in os.listdir(current_dir) if f.endswith(".jsonl")]

for jsonl_file in jsonl_files:
    json_path = os.path.join(current_dir, jsonl_file)
    output_folder = os.path.join(current_dir, os.path.splitext(jsonl_file)[0])
    train_lora(json_path, output_folder)
