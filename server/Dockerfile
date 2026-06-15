FROM node:22-alpine
WORKDIR /app

# Install server dependencies
COPY server/package*.json ./
RUN npm ci --omit=dev

# Copy server source
COPY server/ ./

# Bundle pre-computed chronos data (v2 scores, action plans, herald content)
COPY chronos/data /app/chronos_data
ENV CHRONOS_DATA_DIR=/app/chronos_data

EXPOSE 8000
CMD ["node", "index.js"]
