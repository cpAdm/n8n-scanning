# Large scale Internet scanning with n8n

[![Build custom n8n nodes](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml)
[![Test Docker container](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml)
[![Update n8n version](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml)

## Disclaimer

> [!IMPORTANT]
> This project leverages tools designed for internet-wide network scanning (e.g., Zmap, Masscan, Nmap). It is intended
> STRICTLY for educational and research purposes. You are solely responsible for ensuring that your network operations
> comply with all applicable local, state, and federal laws, and that you have obtained the necessary authorizations
> before scanning any networks or systems you do not own.

## Architecture Overview

This project provides a fully containerized environment for orchestrating large-scale network scans:

- **n8n**: The core workflow automation engine that orchestrates the scanning processes.
- **Custom nodes**: Native integration of popular scanning tools (Zmap, Masscan, Zgrab2, Nmap) directly inside n8n
  workflows.
- **Traefik**: Acts as a reverse proxy, automatically handling HTTPS via Let's Encrypt for the n8n dashboard and contact
  page.
- **Contact page**: A lightweight contact page providing transparency about your scans and a channel to handle IP
  opt-out/blocklist requests.

## Getting started

Get a working container with n8n, the scanning tools, and the contact page:

1. Install the following tools:
    - [Git](https://git-scm.com/install)
    - [Docker Engine](https://docs.docker.com/engine/install/) (Make sure **Docker Compose v2** is available, as this
      project uses `docker compose`)

2. Clone this repository:
    ```bash
    git clone https://github.com/cpAdm/n8n-scanning.git 
    ```

3. Copy `.env.default` to `.env`, and adjust variables where needed:
    1. `DOMAIN_NAME`: the host name where your server is running
    2. `SSL_EMAIL`: the email address to use for the TLS/SSL certificate creation
    3. *Note: You can also configure other n8n environment variables in this file.*

4. Copy `traefik.default.yml` to `traefik/dynamic/traefik.yml`, and replace placeholders:
    1. `DOMAIN_NAME`: the host name where your server is running
    2. `DOMAIN_IP`: the IP of your server

5. Prepare your contact page. Either provide your own files or copy the `/web-template` folder to `/web` and adjust the
   template contact page to match your scanning project and contact details and remove the banner.

6. Build the image and start the container:
    ```shell
    docker compose up -d --build
    ```

You will now have the following features:

- Contact page available at https://DOMAIN_NAME/.
- N8n editor available at https://DOMAIN_NAME/n8n. Create an account and log in to access the n8n workflow
- Redirect any HTTP traffic to use HTTPS. Traefik will automatically generate TLS/SSL certificates for your domain using
  Let's Encrypt.
- Data is persisted using Docker volumes, so you can stop and start the container without losing your n8n workflows,
  certificates, etc.

### Shutting down

Stop the containers when done:

```shell
docker compose down
```

### Firewall

You might run into (VM) firewall issues in order to expose ports 80 and 443. Below is an example for firewall rules to
allow n8n in docker to be accessed from the outside (a reboot might be needed):

```bash
sudo cp nftables.conf /etc/nftables.conf && sudo nft -f /etc/nftables/conf && sudo systemctl enable --now nftables
```

See the new firewall config:

```bash
sudo nft list ruleset
```

## Usage

[//]: # (TODO Add more usage examples on how to get started, include workflow templates, etc.)

Remarks:

- The workflow needs to be published, otherwise the scan is skipped, so e.g. use the schedule trigger to run it at a
  specific time or interval.

### Blocklist

To scan responsibly, allow users to opt out via your contact page. See `data/blocklist.txt` for a list of IPs (with
optionally port number) that already
have [requested in the past](https://gitlab.utwente.nl/m7711402/internet-wide-scans) to opt out.

### Custom n8n nodes

See `./nodes` for all available custom (action) nodes. This includes one for retrieving IP ranges from CSPs and for the
popular scanning tools NMap, ZMap, Zgrab2, and MASSCAN.

When you make changes, build and start the container again with the aforementioned command.

## Analysis of scan results

To quickly analyse the JSONL output of ZGrab2, you can use the bundled [jq](https://jqlang.org/) CLI tool.
See [ZGrab2 schemas](https://github.com/zmap/zgrab2/tree/master/zgrab2_schemas/zgrab2) for the available fields to
query.

For example:

```bash
jq -r '.data.rdp.result.ntlm.os_version' data/2026-03-26T12-00-00-000Z-zgrab2-output.json | sort | uniq -c
```

Additionally, you can use the provided `scripts/main.py` script to get a quick overview per service, (Hilbert prefix)
plots, and CVE enrichment by looking up discovered versions against the NVD API.

```bash
sudo apt-get install python3-pip                              # Install pip if not already installed
python3 -m venv .venv                                         # Create a virtual environment
./.venv/bin/python -m pip install -r scripts/requirements.txt # Install required Python packages in the virtual environment
./.venv/bin/python scripts/main.py --help                     # Run the script with the --help flag to see usage instructions
```

## FAQ

Q1: ZMAP hangs before it actually starts scanning.

A1: It might get stuck at getting the MAC address. Try specifying it yourself with `--gateway-mac` (see
`ip neigh show` for the right value)

## Tips

### Monitor network traffic throughput

Find the right network interface with `ip -br link`, and then monitor the traffic on that interface with:

```bash
ifstat -i eth0 1 
```

# Resources

- [Contribution guide](CONTRIBUTING.md)
- [n8n docs](https://docs.n8n.io/)
