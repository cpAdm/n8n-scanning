# N8N Scanning

[![Build custom n8n nodes](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml)
[![Test Docker container](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml)
[![Update n8n version](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml)

## Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/)

## Docker container

Get a working container with N8N and the scanning tools:

1. Copy `.env.default` to `.env`, and adjust variables where needed:
    1. `DOMAIN_NAME`: the host name where your server is running
    2. `SSL_EMAIL`: the email address to use for the TLS/SSL certificate creation
2. Build image and start the container:
    ```shell
    docker compose -p n8n-scanning up -d --build
    ```

Stop the container when done:

```shell
docker compose down
# Or stop containers separately
docker stop n8n-scanning-traefik-1 n8n-scanning-n8n-1 n8n-scanning-web-1
```

**Features**

- Web service: serves static content at `/` (https://DOMAIN_NAME/)
- n8n: workflow UI at `/n8n` (https://DOMAIN_NAME/n8n) - so no need for extra DNS record for subdomain
- Traefik: reverse proxy with HTTPS (Let’s Encrypt) and HTTP → HTTPS redirection
- Persistence: n8n_data for workflows, traefik_data for certificates

### VM Firewall

Example for firewall rules to allow n8n in docker to be accessed from the outside:

[//]: # (TODO Disallow n8n access outside UT network - remove 5678 port stuff)

```bash
sudo cp nftables.conf /etc/nftables.conf 
sudo nft -f /etc/nftables/conf
sudo systemctl enable --now nftables
```

See config:

```bash
sudo nft list ruleset
```

## Custom N8N nodes

See `./nodes` for all available custom (action) nodes. This includes one for retrieving IP ranges from CSPs and for the
popular scanning tools NMap, ZMap, Zgrab2, and MASSCAN.

When you make changes, build and start the container again with the aforementioned command.