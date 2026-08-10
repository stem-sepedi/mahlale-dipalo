# Project structure

```text
website-shot/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── screenshot.py
├── output/
└── screenshots/
```

---

# docker-compose.yml

```yaml
version: "3.9"

services:
  screenshot:

    build: .

    container_name: screenshot

    volumes:
      - ./screenshots:/screenshots

    environment:
      TZ: Africa/Johannesburg

    command: >
      python3 screenshot.py
      https://example.com
      /screenshots/example.png
```

---

# Dockerfile

```dockerfile
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        wget \
        curl \
        ca-certificates \
        fonts-liberation \
        libnss3 \
        libatk-bridge2.0-0 \
        libgtk-3-0 \
        libgbm1 \
        libasound2 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libdrm2 \
        libxkbcommon0 \
        libxcb1 \
        libxshmfence1 \
        libxext6 \
        libx11-6 \
        && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY . .

CMD ["python3","screenshot.py"]
```

---

# requirements.txt

```text
playwright
```

---

# screenshot.py

```python
#!/usr/bin/env python3

import sys

from playwright.sync_api import sync_playwright


def screenshot(url, outfile):

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1920,
                "height": 1080
            }
        )

        page.goto(
            url,
            wait_until="networkidle",
            timeout=60000
        )

        page.screenshot(
            path=outfile,
            full_page=True
        )

        browser.close()


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage:")
        print("python screenshot.py URL OUTPUT")
        sys.exit(1)

    screenshot(sys.argv[1], sys.argv[2])
```

Run:

```bash
docker compose up --build
```

Produces

```
screenshots/example.png
```

---

# Mobile screenshots

```python
iphone = p.devices["iPhone 15"]

context = browser.new_context(**iphone)

page = context.new_page()
```

---

# Desktop Chrome emulation

```python
browser = p.chromium.launch()

page = browser.new_page(
    viewport={
        "width": 2560,
        "height": 1440
    },
    device_scale_factor=2
)
```

---

# Login example

```python
page.goto("https://mysite/login")

page.fill("#username", "admin")
page.fill("#password", "secret")

page.click("button[type=submit]")

page.wait_for_load_state("networkidle")

page.screenshot(path="dashboard.png", full_page=True)
```

---

# Execute JavaScript

```python
title = page.title()

html = page.content()

page.evaluate("""
document.body.style.background='red';
""")
```

---

# PDF generation (Chromium)

```python
page.pdf(
    path="page.pdf",
    format="A4",
    print_background=True
)
```

---

# Capture many URLs

```python
urls = [
    "https://example.com",
    "https://github.com",
    "https://python.org"
]

for url in urls:

    filename = url.split("//")[1].replace("/", "_") + ".png"

    page.goto(url, wait_until="networkidle")

    page.screenshot(
        path=f"/screenshots/{filename}",
        full_page=True
    )
```

---

# Parallel browser pages

```python
context = browser.new_context()

pages = [context.new_page() for _ in range(10)]

for page, url in zip(pages, urls):
    page.goto(url)

for page in pages:
    page.wait_for_load_state("networkidle")
```

---

# When Selenium is preferable

Use Selenium if you need to:

* Drive an existing Selenium Grid
* Integrate with enterprise browser farms
* Test browser extensions
* Use specialised browser profiles managed by WebDriver

For everything else—especially automated website screenshots, PDF generation, scraping dynamic pages, or browser automation—**Playwright** is generally the better choice. It supports Chromium, Firefox, and WebKit from the same API, automatically waits for page readiness, produces consistent full-page screenshots, and runs very well in Docker.
