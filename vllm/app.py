import os
import re
import math
import torch
import logging
from flask import Flask, request, jsonify
from vllm import LLM, SamplingParams

# --- Configuration Constants ---
MODEL_PATHNAME = os.environ.get("MODEL_PATHNAME", "ibm-granite/granite-guardian-3.2-3b-a800m")
MAX_MODEL_LEN = int(os.environ.get("MAX_MODEL_LEN", 1024))
TENSOR_PARALLEL_SIZE = int(os.environ.get("TENSOR_PARALLEL_SIZE", 1))
TOXICITY_THRESHOLD = float(os.environ.get("TOXICITY_THRESHOLD", 0.75))
DEBUG = os.getenv("DEBUG", True)

CERT_PATH = "/certs/server.crt"
KEY_PATH = "/certs/server.key"

SAFE_TOKEN = "No"
RISKY_TOKEN = "Yes"
DEFAULT_CONFIDENCE = "High"

# --- Risk Categories and Reasons ---
RISK_CATEGORIES = {
    "violence": "description of violent acts",
    "unethical_behavior": "inquiries on how to perform an illegal activity",
    "sexual_content": "sexual content"
}

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("guardian-llm")

# --- App Initialization ---
app = Flask(__name__)
model = None
tokenizer = None
sampling_params = SamplingParams(temperature=0.0, logprobs=20)

def to_json_safe(val):
    """Ensure returned values are JSON-safe (rounded floats or scalars)."""
    return round(val.item() if isinstance(val, torch.Tensor) else val, 3)

def load_model():
    """Load the LLM model and tokenizer."""
    global model, tokenizer
    logger.info(f"Loading model: {MODEL_PATHNAME}")
    model = LLM(model=MODEL_PATHNAME, tensor_parallel_size=TENSOR_PARALLEL_SIZE, max_model_len=MAX_MODEL_LEN)
    tokenizer = model.get_tokenizer()
    logger.info("Model loaded successfully.")

@app.route("/health")
def health():
    """Simple health check route."""
    return ("Loading", 503) if model is None else ("OK", 200)

@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze a given prompt for safety using Granite Guardian."""
    if model is None or tokenizer is None:
        return jsonify({"error": "Model not ready"}), 503

    data = request.get_json()
    user_text = data.get("prompt", "")
    logger.info(f"Analyzing prompt: {user_text}")

    blocked = False
    reason = None
    prob_of_risk = 0.0
    label = SAFE_TOKEN

    for risk_name, explanation in RISK_CATEGORIES.items():
        messages = [{"role": "user", "content": user_text}]
        guardian_config = {"risk_name": risk_name}

        chat = tokenizer.apply_chat_template(
            messages, guardian_config=guardian_config, tokenize=False, add_generation_prompt=True
        )

        output = model.generate(chat, sampling_params, use_tqdm=False)
        result = output[0].outputs[0]
        prob = get_probabilities(result.logprobs)
        prob_of_risk = prob[1]
        label = RISKY_TOKEN if result.text.strip().lower().startswith("yes") else SAFE_TOKEN

        if label == RISKY_TOKEN and prob_of_risk.item() > TOXICITY_THRESHOLD:
            blocked = True
            reason = explanation
            break  # Early exit if any risk is detected

    reply = f"The prompt was blocked because it contained {reason}." if blocked else "Prompt is allowed."

    return jsonify({
        "label": label,
        "confidence": DEFAULT_CONFIDENCE,
        "probability_of_risk": to_json_safe(prob_of_risk),
        "blocked": blocked,
        "reply": reply
    })

def get_probabilities(logprobs):
    """Calculate the probabilities of SAFE vs RISKY using logprobs."""
    safe_token_prob = 1e-50
    risky_token_prob = 1e-50
    for token_group in logprobs:
        for token_prob in token_group.values():
            decoded = token_prob.decoded_token.strip().lower()
            if decoded == SAFE_TOKEN.lower():
                safe_token_prob += math.exp(token_prob.logprob)
            elif decoded == RISKY_TOKEN.lower():
                risky_token_prob += math.exp(token_prob.logprob)

    probs = torch.softmax(
        torch.tensor([math.log(safe_token_prob), math.log(risky_token_prob)]), dim=0
    )
    return probs

if __name__ == "__main__":
    load_model()
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=DEBUG,
        ssl_context=(CERT_PATH, KEY_PATH),
        use_reloader=False
    )
