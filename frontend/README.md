# FAQ Assistant UI

Angular 18 UI application for FAQ Assistant.

## Prerequisites

- For local development: Node.js 20+ and npm 10+
- For containerized build: Docker Engine 24+

## Install & Develop Locally

```bash
npm install
npm start
```

Visit `http://localhost:4200` to view the app. 


## Run with Docker

1. Build the image:
   ```bash
   docker build -t faq-assistant-ui .
   ```

2. Start a container:
   ```bash
   docker run --rm -p 4200:80 faq-assistant-ui
   ```

4. Open `http://localhost:4200` in your browser. The container serves the compiled static files via Nginx.



