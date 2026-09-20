# Production image for the EnerFabric Next.js frontend.
#
# NEXT_PUBLIC_API_URL is inlined into the client bundle at build time by
# Next.js (it's read via process.env in client components — see
# src/lib/config.ts), so it must be supplied as a build ARG, not a
# runtime environment variable. docker-compose.yml passes it through from
# the deployer's own .env file; see README.md.

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
