"""LoRA fine-tune of Qwen3-4B on KRISHI-X farmer speech (routing + yes/no meaning) -> GGUF for Ollama.
Needs a CUDA GPU (free Google Colab T4 works, ~15 min). Not run on the Windows dev PC (no CUDA training stack there).

  pip install unsloth trl datasets
  python scripts/finetune_lora.py backend/qa_reports/finetune.jsonl
  -> krishix-gguf/*.gguf   then in ollama/Modelfile.krishix replace `FROM qwen3:4b` with `FROM ./krishix-gguf/<file>.gguf`
     and run:  ollama create krishix -f ollama/Modelfile.krishix
Grow the data first: run the bug hunter a few times (new paraphrases each run), then app.qa.export_finetune."""
import sys

from datasets import load_dataset
from trl import SFTConfig, SFTTrainer
from unsloth import FastLanguageModel

data = sys.argv[1] if len(sys.argv) > 1 else "backend/qa_reports/finetune.jsonl"
model, tok = FastLanguageModel.from_pretrained("unsloth/Qwen3-4B-unsloth-bnb-4bit", max_seq_length=1024, load_in_4bit=True)
model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=16, lora_dropout=0, target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                                                                                    "gate_proj", "up_proj", "down_proj"])
ds = load_dataset("json", data_files=data, split="train").map(
    lambda r: {"text": tok.apply_chat_template(r["messages"], tokenize=False, enable_thinking=False)})
SFTTrainer(model=model, tokenizer=tok, train_dataset=ds,
           args=SFTConfig(dataset_text_field="text", per_device_train_batch_size=4, gradient_accumulation_steps=2, num_train_epochs=3,
                          learning_rate=2e-4, logging_steps=10, output_dir="krishix-lora", report_to=[])).train()
model.save_pretrained_gguf("krishix-gguf", tok, quantization_method="q4_k_m")
print("done: krishix-gguf/  (see the docstring for the Ollama step)")
