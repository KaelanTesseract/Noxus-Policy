FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm config set fetch-retries 10 && \
    npm config set fetch-retry-mintimeout 20000 && \
    npm config set fetch-retry-maxtimeout 120000 && \
    npm install --fetch-timeout=600000

COPY . .

# Next.js telemetry disable
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME="0.0.0.0"
ENV PORT=3000

RUN npm run build

CMD ["npm", "start"]
