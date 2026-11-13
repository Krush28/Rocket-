"""Training data for fine-tuning the KRISHI-X model, made from the bug hunter's corpus.
Only lines the full system handled correctly in the last hunt are used (their label is verified), plus the hand-written seeds.
Two tasks, same chat format the backend prompts use: tool routing (-> {"calls": [...]}) and yes/no meaning (-> {"meaning": ...}).
Run:  docker compose exec backend python -m app.qa.export_finetune   ->  backend/qa_reports/finetune.jsonl
Then: scripts/finetune_lora.py (Colab / any CUDA GPU) -> GGUF -> ollama/Modelfile.krishix"""
import json
from pathlib import Path

from app.qa import bughunt as BH

ROUTE = {"best_mandi": "best_mandi", "sell_hold": "sell_or_hold", "forecast": "forecast", "add_crop": "add_crop", "sell_it": "create_order",
         "schemes": "show_schemes", "storage": "storage"}
MEANING = {"confirm_yes": "yes", "ready_yes": "yes", "pending_yes": "yes", "pending_no": "no", "store_no": "no", "pending_hedge": "unclear"}
SYSTEM = "You are the brain of KRISHI-X, a farmer selling assistant. Return only the JSON asked for."


def build() -> Path:
    out = BH.OUT
    corpus = json.loads((out / "corpus_last.json").read_text(encoding="utf-8")) if (out / "corpus_last.json").exists() else {}
    failed = {f["text"] for f in json.loads((out / "BUGHUNT.json").read_text(encoding="utf-8")).get("failures", [])} if (out / "BUGHUNT.json").exists() else set()
    rows = []
    for intent, (_, _, _, seeds) in BH.INTENTS.items():
        for text in dict.fromkeys(seeds + corpus.get(intent, [])):
            if text in failed and text not in seeds:
                continue  # unverified label
            if intent in ROUTE:
                user = f"Route this farmer request to tools, in order. Request: {json.dumps(text, ensure_ascii=False)}"
                ans = {"calls": [{"tool": ROUTE[intent], "args": {}}]}
            elif intent in MEANING:
                user = f"A farmer was asked a yes/no question. What does the reply mean? Reply: {json.dumps(text, ensure_ascii=False)}"
                ans = {"meaning": MEANING[intent]}
            else:
                continue
            rows.append({"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user},
                                      {"role": "assistant", "content": json.dumps(ans, ensure_ascii=False)}]})
    path = out / "finetune.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    p = build()
    print(p, sum(1 for _ in p.open(encoding="utf-8")), "examples")
