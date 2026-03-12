# Large scale network scanning with n8n

[![Build custom n8n nodes](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml)
[![Test Docker container](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml)
[![Update n8n version](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml)

## Getting started

Get a working container with n8n, the scanning tools, and the contact page:

1. Install the following tools:
    - [Docker Engine](https://docs.docker.com/engine/install/)

2. Clone this repro
    ```bash
    git clone https://github.com/cpAdm/n8n-scanning.git 
    ```

3. Copy `.env.default` to `.env`, and adjust variables where needed:
    1. `DOMAIN_NAME`: the host name where your server is running
    2. `SSL_EMAIL`: the email address to use for the TLS/SSL certificate creation

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

[//]: # ( The workflow needs to be published, else scan is skipped, so e.g. use the schedule trigger)

### Blocklist

To responsible scan, allow users to opt out via your contact page. See `data/blocklist.txt` for a list of IP's (with
optionally port number) that already
have [requested in the past](https://gitlab.utwente.nl/m7711402/internet-wide-scans) to opt out.

### Custom n8n nodes

See `./nodes` for all available custom (action) nodes. This includes one for retrieving IP ranges from CSPs and for the
popular scanning tools NMap, ZMap, Zgrab2, and MASSCAN.

When you make changes, build and start the container again with the aforementioned command.

# Resources

- [Contribution guide](CONTRIBUTING.md)
- [n8n docs](https://docs.n8n.io/)

## FAQ

Q1: ZMAP hangs before it actually starts scanning.

A1: It might get stuck at getting the MAC address. Try specifying it yourselves with `--gateway-mac` (see
`ip neigh show` for the right value)
