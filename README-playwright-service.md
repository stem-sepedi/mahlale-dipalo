This is a common architecture and scales well. Instead of embedding Playwright into every application container, run it as a dedicated **Screenshot Service**.

```
                   Docker Network

        +-------------------------------+

        +-------------------------------+
        |                               |
        |   App Container               |
        |   PHP / Python / Node         |
        |                               |
        | POST /screenshot              |
        |-----------------------------> |
        |                               |
        |                 FastAPI       |
        |                 Playwright    |
        |                 Chromium      |
        |                               |
        | <-----------------------------|
        |     PNG / JPEG / PDF          |
        +-------------------------------+
```

Advantages:

* only one Chromium installation
* browser process pool can be reused
* application language independent
* easy horizontal scaling
* much lower memory usage

---

# docker-compose.yml

```yaml
version: "3.9"

services:

  screenshot:

    build: ./playwright

    container_name: screenshot-service

    restart: unless-stopped

    ports:
      - "8000:8000"

    networks:
      - backend

  app:

    build: ./app

    depends_on:
      - screenshot

    environment:
      SCREENSHOT_URL: http://screenshot:8000

    networks:
      - backend

networks:
  backend:
```

---

# Directory

```
playwright/

    Dockerfile
    requirements.txt
    app.py
```

---

# requirements.txt

```text
fastapi
uvicorn[standard]
playwright
pydantic
```

---

# Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
        libgtk-3-0 \
        libgbm1 \
        libnss3 \
        libx11-xcb1 \
        libasound2 \
        libdrm2 \
        fonts-liberation && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY app.py .

EXPOSE 8000

CMD [
    "uvicorn",
    "app:app",
    "--host",
    "0.0.0.0",
    "--port",
    "8000"
]
```

---

# app.py

```python
from io import BytesIO

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from playwright.sync_api import sync_playwright

app = FastAPI()


class ScreenshotRequest(BaseModel):
    url: str
    width: int = 1920
    height: int = 1080
    full_page: bool = True


@app.post("/screenshot")
def screenshot(req: ScreenshotRequest):

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": req.width,
                "height": req.height
            }
        )

        page.goto(
            req.url,
            wait_until="networkidle",
            timeout=60000
        )

        image = page.screenshot(
            full_page=req.full_page,
            type="png"
        )

        browser.close()

    return StreamingResponse(
        BytesIO(image),
        media_type="image/png"
    )
```

---

# Calling from another container

Python

```python
import requests

r = requests.post(
    "http://screenshot:8000/screenshot",
    json={
        "url":"https://example.com"
    }
)

open("example.png","wb").write(r.content)
```

---

PHP

```php
<?php

$data = [
    "url" => "https://example.com"
];

$ch = curl_init("http://screenshot:8000/screenshot");

curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    "Content-Type: application/json"
]);

curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

$image = curl_exec($ch);

file_put_contents("example.png", $image);
```

---

NodeJS

```javascript
const axios = require("axios");
const fs = require("fs");

(async ()=>{

    const response = await axios.post(
        "http://screenshot:8000/screenshot",
        {
            url:"https://example.com"
        },
        {
            responseType:"arraybuffer"
        }
    );

    fs.writeFileSync("page.png", response.data);

})();
```

---

## Recommended improvements for production

For higher throughput and lower latency:

* **Launch Chromium once at startup** and reuse a single browser instance instead of launching a new one per request.
* **Create a new browser context per request** to isolate cookies, storage, and cache between users.
* **Limit concurrent requests** with an `asyncio.Semaphore` to prevent resource exhaustion.
* **Add authentication** (API key or JWT) if the service is exposed beyond a trusted Docker network.
* **Support additional output formats** such as PNG, JPEG, WebP, and PDF.
* **Accept optional parameters** like custom headers, cookies, viewport size, dark/light mode, device emulation, and CSS media type.
* **Implement health endpoints** (`/health`, `/ready`) for orchestration systems.
* **Return structured JSON errors** when navigation or rendering fails.

With browser reuse, a single service can often handle dozens of screenshots per minute while keeping latency significantly lower than launching a fresh Chromium process for every request.
