# A Reverse proxy for OpenAI (ALLTRUE - Exercise)


## SSL Certificate Setup for AllTrue Project

How to generate self-signed SSL certificates to securely enable HTTPS communication across services 

---

### Directory Structure

Certificates should live in: `./nginx/certs/`

```
nginx/certs/
├── guardian_openssl.cnf
├── nginx_openssl.cnf
```

---

### Step 1: Create OpenSSL Configuration Files

Locate nginx/certs directory

### Step 2: Generate Certificates

#### Run the following commands inside the `nginx/certs` directory:

```bash
# Generate Guardian cert & key
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout guardian.key \
  -out guardian.crt \
  -config guardian_openssl.cnf

# Generate Nginx cert & key
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout server.key \
  -out server.crt \
  -config nginx_openssl.cnf
```

> Make sure to run these commands in the same directory as the config files.

```
nginx/certs/
├── guardian.crt
├── guardian.key
├── server.crt
├── server.key
├── guardian_openssl.cnf
├── nginx_openssl.cnf
```

> Finally you will get certs as above

---

