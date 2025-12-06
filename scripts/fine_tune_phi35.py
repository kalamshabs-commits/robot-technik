import os
import json
import pandas as pd
import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from peft import LoraConfig, get_peft_model

def load_cases(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    def add_case(c):
        device = c.get("device_type", "")
        brand = c.get("brand", "")
        model = c.get("model", "")
        symptom = c.get("symptom") or c.get("title") or ""
        cause = c.get("cause") or ""
        solution = c.get("solution") or ""
        if not solution:
            steps = c.get("steps") or []
            solution = "; ".join(steps)
        instr = "Диагностируй неисправность и предложи решение"
        inp = f"Тип: {device}; Бренд: {brand}; Модель: {model}; Симптом: {symptom}; Причина: {cause}"
        out = solution
        rows.append({"instruction": instr, "input": inp, "output": out})
    for group in ["smartphones","laptops","microwaves","printers","breadmakers","multicookers"]:
        g = data.get(group, {})
        if isinstance(g, dict):
            for k,v in g.items():
                if k == "models":
                    continue
                if isinstance(v, list):
                    for it in v:
                        add_case(it)
            m = g.get("models")
            if isinstance(m, list):
                for it in m:
                    add_case(it)
    return rows

def build_dataset(rows, tokenizer):
    df = pd.DataFrame(rows)
    ds = Dataset.from_pandas(df)
    def format_fn(ex):
        text = f"### Instruction:\n{ex['instruction']}\n\n### Input:\n{ex['input']}\n\n### Output:\n{ex['output']}"
        tok = tokenizer(text, truncation=True, max_length=2048)
        tok["labels"] = tok["input_ids"].copy()
        return tok
    return ds.map(format_fn, remove_columns=ds.column_names)

def main():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    faults_path = os.path.join(base_dir, "faults_library.json")
    rows = load_cases(faults_path)
    model_name = "microsoft/Phi-3.5-mini-instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
    lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj","v_proj"])
    model = get_peft_model(model, lora)
    ds = build_dataset(rows, tokenizer)
    out_dir = os.path.join(base_dir, "backend", "models", "phi35_lora_adapter")
    os.makedirs(out_dir, exist_ok=True)
    args = TrainingArguments(
        output_dir=os.path.join(out_dir, "trainer_out"),
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        fp16=False,
        bf16=True,
        logging_steps=50,
        save_steps=500,
        save_total_limit=2,
        report_to=[]
    )
    trainer = Trainer(model=model, args=args, train_dataset=ds)
    trainer.train()
    model.save_pretrained(out_dir)

if __name__ == "__main__":
    main()