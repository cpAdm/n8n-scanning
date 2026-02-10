# Large scale network scanning with n8n

[![Build custom n8n nodes](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml)
[![Test Docker container](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml)
[![Update n8n version](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml)

## Getting started

Get a working container with n8n and the scanning tools:

1. Install the following tools:
    - [Docker Engine](https://docs.docker.com/engine/install/)

2. Clone this repro
    ```bash
    git clone https://github.com/cpAdm/n8n-scanning.git 
    ```

3. Copy `.env.default` to `.env`, and adjust variables where needed:
    1. `DOMAIN_NAME`: the host name where your server is running
    2. `SSL_EMAIL`: the email address to use for the TLS/SSL certificate creation

4. Prepare your contact page. Either provide your own files or copy the `/web-template` folder to `/web` and adjust the
   template contact page to match your scanning project and contact details and remove the banner.

5. Build the image and start the container:
    ```shell
    docker compose -p n8n-scanning up -d --build
    ```

The contact page will now be available at https://DOMAIN_NAME/ and the n8n workflow UI at https://DOMAIN_NAME/n8n. HTTP
traffic is automatically redirected to use HTTPS and data (n8n workflows, Traefik, certificates, etc.) is persisted
using Docker volumes.

### Shutting down

Stop the container when done:

```shell
docker compose down
# Or stop containers separately
docker stop n8n-scanning-traefik-1 n8n-scanning-n8n-1 n8n-scanning-web-1
```

### VM Firewall

You might run into firewall issues in order to expose ports 80 and 443. Below is an example for firewall rules to allow
n8n in docker to be accessed from the outside (a reboot might be needed):

```bash
sudo cp nftables.conf /etc/nftables.conf && sudo nft -f /etc/nftables/conf && sudo systemctl enable --now nftables
```

See firewall config:

```bash
sudo nft list ruleset
```

## Usage

[//]: # (TODO Add more usage examples on how to get started, include workflow templates, etc.)

### Custom n8n nodes

See `./nodes` for all available custom (action) nodes. This includes one for retrieving IP ranges from CSPs and for the
popular scanning tools NMap, ZMap, Zgrab2, and MASSCAN.

When you make changes, build and start the container again with the aforementioned command.