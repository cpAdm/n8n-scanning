ARG N8N_VERSION=1.118.2
# TODO Github action to trigger PR when new verison is available for N8N?

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

# Switch back to the default non-root user
# TODO save user name instead, and load here?
USER node

# Do not change the CMD and ENTRYPOINT from the base image
