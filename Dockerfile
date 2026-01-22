# GitHub workflow automatically creates a PR whenever new version is released
ARG N8N_VERSION=2.4.4

FROM node:24-alpine AS nodes-builder

# Compile our n8n-nodes and add them as well
COPY /n8n-nodes /tmp/custom-nodes
WORKDIR /tmp/custom-nodes
RUN npm ci --include=dev
RUN npm run build


FROM n8nio/n8n:${N8N_VERSION}

# We need root access for some scanning tools
USER root

# Re-install package manager (n8n image has apk-tools removed)
# https://github.com/n8n-io/n8n/blob/bc7ec87a5bbb995d777a9e1eb2290796d59c1b5e/docker/images/n8n-base/Dockerfile#L29C2-L29C22
RUN set -eux; \
    ALPINE_VER="v$(grep '^VERSION_ID=' /etc/os-release | cut -d= -f2)"; \
    ARCH="$(uname -m)"; \
    BASE_URL="https://dl-cdn.alpinelinux.org/alpine/$ALPINE_VER/main/$ARCH"; \
    wget "$BASE_URL/APKINDEX.tar.gz"; \
    tar -xzf APKINDEX.tar.gz; \
    APK_FILE="$(grep -A1 '^P:apk-tools-static$' APKINDEX | grep '^V:' | cut -d: -f2)"; \
    wget "$BASE_URL/apk-tools-static-$APK_FILE.apk"
RUN tar -xzf apk-tools-static-*.apk
RUN cp sbin/apk.static /sbin/apk
RUN chmod +x /sbin/apk
RUN /sbin/apk version
RUN apk add --no-cache apk-tools
RUN rm -rf apk-tools-static-*.apk sbin

# Install scanning tools
# Note that we cannot pin these package versions, as Alpine might drop old versions
# https://gitlab.alpinelinux.org/alpine/abuild/-/issues/9996
# https://pkgs.alpinelinux.org/packages
RUN apk add --no-cache \
    nmap \
    masscan libpcap libpcap-dev \
    zmap \
    tcpdump

ENV N8N_CUSTOM_EXTENSIONS=/data/custom
RUN mkdir -p /data/custom
COPY --from=nodes-builder /tmp/custom-nodes/dist /data/custom/

# We cannot switch back to the default non-root user, as some scans like (nmap -sS) requires sudo priviliges
# Do not change the CMD and ENTRYPOINT from the base image
