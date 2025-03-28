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
## Prerequisites
- This set of applications were tested with the following configurations
    - docker = (25.0.8) 
    - docker compose (v2.24.6)
    - CPU = 16vCPU 
    - RAM = 128G
    - SSD = 100G
    - OS  = Linux ip-172-31-31-152.ec2.internal 6.1.130-139.222.amzn2023.x86_64

## Project Structure
```
alltrue/
├── app/                # Client Flask app
├── mitmproxy/          # Interceptor module for mitmproxy
├── nginx/              # NGINX config and SSL certs
├── vllm/               # Guardian app with LLM (this is a clone of https://github.com/vllm-project/vllm.git)
├── docker-compose.yml  # Service definitions
```

---

## Clone https://github.com/vllm-project/vllm.git

Run the following commands to clone and adopt to this project

```bash
cd vllm
chmod +x ./clone-vllm.sh
sh ./clone-vllm.sh
```

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

app
```
OPENAI_API_KEY - Use a valid open api key 
OPENAI_MODEL - gpt-3.5-turbo or use a latest one
```

mitm
```
TIME_OUT - use a higher value such as 30 if the guardian is slow
```

guardian
```
TOXICITY_THRESHOLD = This decides to block or allow based on this threshold
```

Let other environment varibles in all services be as they are

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

## Client UI
To access the client UI:
```bash
http://<IP>:5000
```


---

## Application Behavior
- All requests go to NGINX (HTTPS).
- NGINX forwards `/v1/` to `mitmproxy`, others to the Flask app.
- `mitmproxy` intercepts requests and responses to `api.openai.com`, calls Guardian to evaluate.
- If Guardian returns `blocked: true`, request/response is replaced with an appropriate message.

---

