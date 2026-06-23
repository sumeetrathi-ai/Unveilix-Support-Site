# Change log:
# [#001] 2026-06-23 — Sumeet — Export the VITE_API_URL build ARG as an ENV so `vite build`
#         reads the value passed by compose (not the committed frontend/.env, which was
#         removed). This stops a localhost default from leaking into production builds.

# Stage 0, "build-stage", based on Bun, to build and compile the frontend
FROM oven/bun:1 AS build-stage

WORKDIR /app

COPY package.json bun.lock /app/

COPY frontend/package.json /app/frontend/

WORKDIR /app/frontend

RUN bun install

COPY ./frontend /app/frontend

# [#001] --by Sumeet (2026-06-23)
# Before: `ARG VITE_API_URL` only — not exported, so vite read it from frontend/.env
#         (hard-coded http://localhost:8000).
# After: also export it as an env var so vite bakes the compose-provided value
#         (local override: http://localhost:8000; prod: https://api.${DOMAIN}).
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

RUN bun run build


# Stage 1, based on Nginx, to have only the compiled app, ready for production with Nginx
FROM nginx:1

COPY --from=build-stage /app/frontend/dist/ /usr/share/nginx/html

COPY ./frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY ./frontend/nginx-backend-not-found.conf /etc/nginx/extra-conf.d/backend-not-found.conf
