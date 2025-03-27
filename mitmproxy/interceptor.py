import json
import requests
from mitmproxy import http
import os

GUARDIAN_URL = os.getenv("GUARDIAN_URL", "https://guardian:5001/analyze")
CERT_PATH = "/usr/local/share/ca-certificates/guardian.crt"
TIME_OUT = int(os.getenv("TIME_OUT", 15))

print("MITM Running...")

class OpenAIInterceptor:
    def request(self, flow: http.HTTPFlow):
        if "api.openai.com" in flow.request.pretty_host:
            try:
                content = flow.request.get_text()
                if not content:
                    print("[Interceptor ERROR] Empty content")
                    return

                print("Content:", content)
                data = json.loads(content)
                prompt = data["messages"][-1]["content"]

                print("Request to guardian:", prompt)
                result = self.analyze_prompt(prompt)
                print("Result from analyze:", result)

                if result["blocked"]:
                    reason = result["reason"]
                    blocked_response = {
                        "choices": [{
                            "message": {
                                "role": "assistant",
                                "content": reason
                            }
                        }]
                    }

                    flow.response = http.Response.make(
                        200,
                        json.dumps(blocked_response),
                        {"Content-Type": "application/json"}
                    )
                    print(f"[REQUEST BLOCKED] {prompt} → {reason}")
                    return 

            except Exception as e:
                print(f"[Interceptor ERROR] {e}")

    def response(self, flow: http.HTTPFlow):
        if "api.openai.com" in flow.request.pretty_host:
            try:
                content = flow.response.get_text()
                if not content:
                    print("[Interceptor ERROR] Empty response")
                    return

                print("OpenAI Response:", content)
                data = json.loads(content)
                message = data["choices"][0]["message"]["content"]

                print("Sending OpenAI response to Guardian:", message)
                result = self.analyze_prompt(message)
                print("Guardian result on response:", result)

                if result["blocked"]:
                    reason = result["reason"]
                    flow.response = http.Response.make(
                        200,
                        json.dumps({
                            "choices": [{
                                "message": {
                                    "role": "assistant",
                                    "content": reason
                                }
                            }]
                        }),
                        {"Content-Type": "application/json"}
                    )
                    print(f"[RESPONSE BLOCKED] → {reason}")
                    return
            except Exception as e:
                print(f"[Response Interceptor ERROR] {e}")


    def analyze_prompt(self, prompt):
        try:
            res = requests.post(
                GUARDIAN_URL,
                json={"prompt": prompt},
                timeout=TIME_OUT,
                verify=CERT_PATH
            )
            result = res.json()
            if result.get("blocked"):
                return {
                    "blocked": True,
                    "reason": result.get("reply", "The prompt is considered toxic.")
                }
        except Exception as e:
            print(f"[Risk Service ERROR] {e}")

        return {"blocked": False, "reason": None}


addons = [OpenAIInterceptor()]
