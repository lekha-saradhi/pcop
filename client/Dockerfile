FROM node:22-alpine AS builder
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
ENV CI=true
COPY pnpm-lock.yaml package.json .npmrc ./
RUN pnpm install --ignore-scripts || true
ARG API_BACKEND_URL
ENV API_BACKEND_URL=$API_BACKEND_URL
COPY . .
RUN ./node_modules/.bin/next build

FROM node:22-alpine AS runner
RUN corepack enable && corepack prepare pnpm@latest --activate
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts
EXPOSE 3000
CMD ["./node_modules/.bin/next", "start"]