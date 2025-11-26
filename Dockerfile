# GitHub workflow automatically creates a PR whenever new version is released
ARG N8N_VERSION=1.121.2

FROM n8nio/n8n:${N8N_VERSION}

# Switch to root to install scanning tools
# TODO needed?
USER root

# Note that we cannot pin these package versions, as Alpine might drop old versions
# https://gitlab.alpinelinux.org/alpine/abuild/-/issues/9996
# https://pkgs.alpinelinux.org/packages
RUN apk add --no-cache \
    nmap \
    masscan \
    zmap

# Compile our n8n-nodes and add them as well
COPY /n8n-nodes /tmp/custom-nodes
WORKDIR /tmp/custom-nodes
RUN npm ci --include=dev
RUN npm run build

ENV N8N_CUSTOM_EXTENSIONS=/data/custom
RUN mkdir -p /data/custom && cp -r dist/* /data/custom/
WORKDIR /

# TODO Investigate if we can make the image smaller (muliti-stage builds)

# Switch back to the default non-root user
# Do not change the CMD and ENTRYPOINT from the base image
USER node
