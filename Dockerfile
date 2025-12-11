# GitHub workflow automatically creates a PR whenever new version is released
ARG N8N_VERSION=1.121.0

FROM node:24-alpine AS nodes-builder

# Compile our n8n-nodes and add them as well
COPY /n8n-nodes /tmp/custom-nodes
WORKDIR /tmp/custom-nodes
RUN npm ci --include=dev
RUN npm run build


FROM n8nio/n8n:${N8N_VERSION}

# Switch to root to install scanning tools
USER root

# Note that we cannot pin these package versions, as Alpine might drop old versions
# https://gitlab.alpinelinux.org/alpine/abuild/-/issues/9996
# https://pkgs.alpinelinux.org/packages
RUN apk add --no-cache \
    nmap \
    masscan libpcap libpcap-dev \
    zmap

ENV N8N_CUSTOM_EXTENSIONS=/data/custom
RUN mkdir -p /data/custom
COPY --from=nodes-builder /tmp/custom-nodes/dist /data/custom/

# We cannot switch back to the default non-root user, as some scans like (nmap -sS) requires sudo priviliges
# Do not change the CMD and ENTRYPOINT from the base image
