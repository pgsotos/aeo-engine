# aeo-engine frontend — Next.js 16 (App Router).
# Dependencies are installed with Bun (matches local dev + the lockfile);
# the build and runtime use Node, since `bun run build` segfaults on some
# Linux/arch combos.

FROM oven/bun:1.3 AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

FROM node:22-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* is inlined at build time, so the backend URL must be known here.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
# Opt into `output: "standalone"` (see frontend/next.config.ts) for a slim image.
ENV BUILD_STANDALONE=1
RUN node ./node_modules/next/dist/bin/next build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
# `output: "standalone"` produces a minimal server + its traced dependencies.
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
