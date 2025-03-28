# AllTrue Proxy System - Reverse Proxy to OpenAI with Guardian

This system is designed to act as a secure reverse proxy between clients and OpenAI's API. It uses `mitmproxy` to intercept requests and responses, evaluates them using IBM's Granite Guardian model (running via `vllm`), and blocks inappropriate content based on defined criteria. It supports full SSL encryption.

---

## Features
- Intercepts both prompts and responses.
- Uses Guardian to detect:
  - Violent content
  - Illegal activity inquiries
  - Sexual content
  - Toxicity (general)
- Blocks flagged content with appropriate warning messages.
- HTTPS support end-to-end via NGINX termination.

---

## Project Structure
```
alltrue/
├── app/                # Client Flask app
├── mitmproxy/          # Interceptor module for mitmproxy
├── nginx/              # NGINX config and SSL certs
├── vllm-main/          # Guardian app with LLM
├── docker-compose.yml  # Service definitions
```

---

## Generate Certificates
### Step 1: Location

Locate nginx/certs directory

### Step 2: Generate Cert and Key
```bash
cd nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key -out server.crt \
  -config nginx_openssl.cnf
```

```bash
cd nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout guardian.key -out guardian.crt \
  -config guardian_openssl.cnf
```


## Required modifications in docker-compose.yml

Client
OPENAI_API_KEY - Use a valid open api key 
OPENAI_MODEL - gpt-3.5-turbo or use a latest one

mitm
TIME_OUT - use a higher value such as 30 if the guardian is slow

guardian
TOXICITY_THRESHOLD = This decides to block or allow based on this threshold

Let other environment varibles be as they are

---

## How to Run
### Start all services
```bash
docker compose up --build -d
```

### Stop and remove containers and volumes
```bash
docker compose down -v
```

### Check container status
```bash
docker ps
```

### Get logs for a specific container
```bash
docker logs <container_name>

# Example:
docker logs mitm
docker logs guardian
docker logs app
docker logs nginx
```

---

## Health Check
Ensure Guardian is working:
```bash
curl -k https://localhost:5001/health
```

Test Guardian API manually:

```bash
curl --cacert nginx/certs/guardian.crt https://localhost:5001/analyze \
  -H "Content-Type: application/json" \
  -d '{"prompt": "how to make a bomb"}'
```

---

## Application Behavior
- All requests go to NGINX (HTTPS).
- NGINX forwards `/v1/` to `mitmproxy`, others to the Flask app.
- `mitmproxy` intercepts requests and responses to `api.openai.com`, calls Guardian to evaluate.
- If Guardian returns `blocked: true`, request/response is replaced with an appropriate message.

---

