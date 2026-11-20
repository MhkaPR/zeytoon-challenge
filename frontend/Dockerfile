FROM node:22-alpine AS dependencies
WORKDIR /app
RUN corepack enable
COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile

FROM node:22-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN yarn build

# nginx is the public entrypoint: it serves the Next.js app and routes /api to Django.
FROM nginx:1.27-alpine AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=127.0.0.1 \
    PORT=3001

# The standalone server needs the Node runtime; install it in the nginx image.
# Alpine's default CDN is filtered on this network; use the Liara mirror. The mirror
# caches upstream lazily, so a cold index can 404 once; retry a few times.
ARG APK_MIRROR=https://linux-mirror.liara.ir/repository/alpine
RUN set -eu; \
    sed -i "s|https\?://dl-cdn.alpinelinux.org/alpine|${APK_MIRROR}|g" /etc/apk/repositories; \
    for attempt in 1 2 3 4 5; do \
        if apk add --no-cache nodejs; then \
            exit 0; \
        fi; \
        echo "apk add failed (attempt ${attempt}); retrying in 10s"; \
        sleep 10; \
    done; \
    exit 1

WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY nginx.conf /etc/nginx/nginx.conf

COPY --chmod=755 <<'EOF' /usr/local/bin/entrypoint
#!/bin/sh
set -eu

# Next.js standalone server listens privately on 3001; nginx owns port 3000.
node /app/server.js &
next_pid=$!

shutdown() {
    kill "$next_pid" 2>/dev/null || true
    nginx -s quit 2>/dev/null || true
}
trap shutdown TERM INT

nginx -g 'daemon off;' &
nginx_pid=$!

# If either process dies, stop the container so Compose can restart it.
while kill -0 "$next_pid" 2>/dev/null && kill -0 "$nginx_pid" 2>/dev/null; do
    sleep 2
done

shutdown
wait 2>/dev/null || true
exit 1
EOF

EXPOSE 3000
CMD ["/usr/local/bin/entrypoint"]
