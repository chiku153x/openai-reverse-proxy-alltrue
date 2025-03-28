import os
import json
import logging
import requests
from mitmproxy import http

# --- Configuration ---
GUARDIAN_URL = os.getenv("GUARDIAN_URL", "https://guardian:5001/analyze")
CERT_PATH = "/usr/local/share/ca-certificates/guardian.crt"
TIMEOUT = int(os.getenv("TIMEOUT", 15))
API_HOST = "api.openai.com"

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("proxy")
logger.info("MITM Proxy started")

class OpenAIInterceptor:

    def request(self, flow: http.HTTPFlow):
        """
        Check the user's prompt before it goes to OpenAI.
        If it is risky, block it and send a warning instead.
        """
        if API_HOST in flow.request.pretty_host:
            try:
                body = flow.request.get_text()
                if not body:
                    logger.warning("No content in request")
                    return

                data = json.loads(body)
                prompt = data["messages"][-1]["content"]
                logger.info("Prompt: %s", prompt)

                result = self.check_with_guardian(prompt)
                logger.info("Prompt check result: %s", result)

                if result["blocked"]:
                    # Replace OpenAI reply with custom warning
                    warning = {
                        "choices": [{
                            "message": {
                                "role": "assistant",
                                "content": result["reason"]
                            }
                        }]
                    }
                    flow.response = http.Response.make(
                        200,
                        json.dumps(warning),
                        {"Content-Type": "application/json"}
                    )
                    logger.warning("Blocked prompt: %s", prompt)

            except Exception as e:
                logger.error("Error in request: %s", str(e))

    def response(self, flow: http.HTTPFlow):
        """
        Check OpenAI's response before it reaches the user.
        If it is risky, replace it with a warning.
        """
        if API_HOST in flow.request.pretty_host:
            try:
                body = flow.response.get_text()
                data = json.loads(body)
                reply = data["choices"][0]["message"]["content"]
                logger.info("Response: %s", reply)

                result = self.check_with_guardian(reply)
                logger.info("Response check result: %s", result)

                if result["blocked"]:
                    data["choices"][0]["message"]["content"] = (
                        "***Response was blocked by Guardian***\n" + result["reason"]
                    )
                    flow.response.set_text(json.dumps(data))
                    logger.warning("Blocked response: %s", reply)

            except Exception as e:
                logger.error("Error in response: %s", str(e))

    def check_with_guardian(self, text):
        """
        Send text to Guardian and return result with block status and reason.
        """
        try:
            response = requests.post(
                GUARDIAN_URL,
                json={"prompt": text},
                timeout=TIMEOUT,
                verify=CERT_PATH
            )
            result = response.json()
            return {
                "blocked": result.get("blocked", False),
                "reason": result.get("reply", "The content was considered harmful.")
            }
        except Exception as e:
            logger.error("Guardian check failed: %s", str(e))
            return {"blocked": False, "reason": None}

# --- Register ---
addons = [OpenAIInterceptor()]
