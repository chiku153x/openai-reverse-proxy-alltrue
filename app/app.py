from flask import Flask, render_template, request, jsonify
import requests
import os
import logging

app = Flask(__name__)

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-xxx")
PROXY_URL = os.getenv("PROXY_URL", "https://nginx/v1/chat/completions")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
DEBUG = os.getenv("DEBUG", True)
SSL_CERT_PATH = "/certs/server.crt"
TEMPERATURE = 0.7

# --- Setup Request CA ---
os.environ["REQUESTS_CA_BUNDLE"] = SSL_CERT_PATH

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO if DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("client-app")

# --- Constants ---
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json"
}
ERROR_INVALID_ENDPOINT = {"error": "Invalid endpoint. Use /send"}

# --- Routes ---

@app.route('/')
def index():
    """Serve the main HTML page."""
    logger.info("Serving index.html")
    return render_template('index.html')

@app.route("/", methods=["POST"])
def invalid_post():
    """Handle accidental POST to root path."""
    logger.warning("POST to invalid route '/'")
    return jsonify(ERROR_INVALID_ENDPOINT), 400

@app.route('/send', methods=['POST'])
def send_prompt():
    """Send user prompt to OpenAI via proxy and return the response."""
    data = request.get_json()
    prompt = data.get('prompt', '')

    if not prompt:
        logger.warning("Missing prompt in request")
        return jsonify({'error': 'Prompt is missing.'}), 400

    logger.info(f"Received prompt: {prompt}")

    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": TEMPERATURE
    }

    try:
        response = requests.post(PROXY_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        response_json = response.json()

        content = response_json['choices'][0]['message']['content']
        logger.info(f"OpenAI response: {content[:100]}...") 
        return {'response': content}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return jsonify({'error': f"Request failed: {str(e)}"}), 502
    except (KeyError, IndexError) as e:
        logger.error(f"Response parsing error: {str(e)}")
        return jsonify({'error': f"Unexpected response format: {str(e)}"}), 500
    except Exception as e:
        logger.exception("Unhandled exception occurred")
        return jsonify({'error': str(e)}), 500

# --- App Runner ---
if __name__ == "__main__":
    logger.info("Starting client app...")
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
