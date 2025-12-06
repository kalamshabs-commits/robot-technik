import os
from llama_cpp import Llama

def load_model():
    base = os.path.join(os.path.dirname(__file__), "models", "phi35_lora_adapter")
    adapter_path = os.path.join(base, "adapter_model.bin")
    model_path = os.getenv("LLAMA_MODEL_PATH", "")
    if not model_path:
        raise RuntimeError("LLAMA_MODEL_PATH env var is required for base model")
    return Llama(model_path=model_path, lora_path=adapter_path, n_ctx=4096)

def generate(prompt: str):
    llm = load_model()
    out = llm(prompt=prompt, max_tokens=256, temperature=0.2)
    txt = out.get("choices", [{}])[0].get("text", "")
    return txt