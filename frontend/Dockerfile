FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm config set registry https://registry.npmjs.org/ && \
    npm config set fetch-retries 10 && \
    npm config set fetch-retry-mintimeout 5000 && \
    npm config set fetch-retry-maxtimeout 60000 && \
    npm config set maxsockets 5 && \
    (npm ci --no-audit --no-fund || npm install --no-audit --no-fund --fetch-timeout=600000)

COPY . .

# Next.js telemetry disable
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

RUN npm run build

CMD ["npm", "start"]
