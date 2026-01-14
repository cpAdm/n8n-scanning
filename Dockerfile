# GitHub workflow automatically creates a PR whenever new version is released
ARG N8N_VERSION=2.2.4

FROM node:24-alpine AS nodes-builder

# Compile our n8n-nodes and add them as well
COPY /n8n-nodes /tmp/custom-nodes
WORKDIR /tmp/custom-nodes
RUN npm ci --include=dev
RUN npm run build

# Install the scanning tools (cannot be done in n8n stage below, as that image no longer has the package manager installed)
# https://github.com/n8n-io/n8n/blob/bc7ec87a5bbb995d777a9e1eb2290796d59c1b5e/docker/images/n8n-base/Dockerfile#L29C2-L29C22
FROM alpine:3.22 AS tools

# Note that we cannot pin these package versions, as Alpine might drop old versions
# https://gitlab.alpinelinux.org/alpine/abuild/-/issues/9996
# https://pkgs.alpinelinux.org/packages
RUN apk add --no-cache \
    nmap \
    masscan libpcap libpcap-dev \
    zmap

FROM n8nio/n8n:${N8N_VERSION}

# We need root access for some scanning tools
USER root

# TODO instead, try to re-install apk-tools
# wget https://dl-cdn.alpinelinux.org/alpine/latest-stable/main/$(uname -m)/apk-tools-static-*.apk
# tar -xzf apk-tools-static-*.apk
# cp sbin/apk.static /sbin/apk
# chmod +x /sbin/apk
# /sbin/apk version
# apk add --no-cache apk-tools
# rm -rf apk-tools-static-*.apk sbin

# We need to copy all scanning tools and its dependencies
COPY --from=tools /usr/bin/nmap /usr/bin/
COPY --from=tools /usr/bin/masscan /usr/bin/
COPY --from=tools /usr/lib/libpcap.so* /usr/lib/
COPY --from=tools /usr/sbin/zmap /usr/sbin/

# Shared dependencies
COPY --from=tools /usr/lib/libpcap.so.1 /usr/lib/

# Nmap (RUN ldd /usr/bin/nmap)
COPY --from=tools /usr/lib/libssh2.so.1 /usr/lib/
COPY --from=tools /usr/lib/libssl.so.3 /usr/lib/
COPY --from=tools /usr/lib/libcrypto.so.3 /usr/lib/
COPY --from=tools /usr/lib/libz.so.1 /usr/lib/
COPY --from=tools /usr/lib/liblua-5.4.so.0 /usr/lib/
COPY --from=tools '/usr/lib/libstdc++.so.6' /usr/lib/
COPY --from=tools /usr/lib/libgcc_s.so.1 /usr/lib/
COPY --from=tools /usr/share/nmap /usr/share/nmap

# ZMap (RUN ldd /usr/sbin/zmap)
COPY --from=tools /usr/lib/libgmp.so.10 /usr/lib/
COPY --from=tools /usr/lib/libunistring.so.5 /usr/lib/
COPY --from=tools /usr/lib/libjson-c.so.5 /usr/lib/
COPY --from=tools /usr/lib/libJudy.so.1 /usr/lib/
# TODO needed for zmap?
#ENV PATH="/usr/sbin:${PATH}"

ENV N8N_CUSTOM_EXTENSIONS=/data/custom
RUN mkdir -p /data/custom
COPY --from=nodes-builder /tmp/custom-nodes/dist /data/custom/

# We cannot switch back to the default non-root user, as some scans like (nmap -sS) requires sudo priviliges
# Do not change the CMD and ENTRYPOINT from the base image
