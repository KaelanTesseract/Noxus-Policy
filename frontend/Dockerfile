# Node 20 reached end of life in April 2026; 24 is the current LTS line.
FROM node:25-slim

# Everything below - install, build and the running server - happens as the
# unprivileged "node" user that ships with the image, never as root.
RUN mkdir -p /app && chown node:node /app
WORKDIR /app
USER node

COPY --chown=node:node package.json package-lock.json* ./
RUN npm config set registry https://registry.npmjs.org/ && \
    npm config set fetch-retries 10 && \
    npm config set fetch-retry-mintimeout 5000 && \
    npm config set fetch-retry-maxtimeout 60000 && \
    npm config set maxsockets 5
# Retry `npm ci` on flaky networks (Proxmox LXC) instead of falling back to
# `npm install`, which is allowed to drift from package-lock.json.
RUN ok=0; \
    for attempt in 1 2 3; do \
      if npm ci --no-audit --no-fund --fetch-timeout=600000; then ok=1; break; fi; \
      echo "npm ci failed (attempt $attempt), retrying..."; sleep 5; \
    done; \
    [ "$ok" = "1" ]

COPY --chown=node:node . .

# Next.js telemetry disable
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

RUN npm run build

CMD ["npm", "start"]
