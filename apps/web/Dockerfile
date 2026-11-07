# Contexto de build: raíz del repo (usa el package-lock del monorepo).
#   docker build -f apps/web/Dockerfile -t predictions-web .
FROM node:22-alpine AS build
WORKDIR /repo
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
# CA opcional para redes con proxy TLS (secret "extra_ca"); no queda en la imagen.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    npm ci --workspace apps/web --include-workspace-root=false
COPY apps/web apps/web
ARG VITE_API_URL=/backend
ENV VITE_API_URL=${VITE_API_URL}
RUN npm --workspace apps/web run build

FROM nginx:1.27-alpine
COPY apps/web/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /repo/apps/web/dist /usr/share/nginx/html
# Destino de /backend (la API). En docker compose es el servicio "api".
ENV API_UPSTREAM=http://api:8000
EXPOSE 80
