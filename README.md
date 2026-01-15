# N8N Scanning

[![Build custom n8n nodes](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/build-nodes.yml)
[![Test Docker container](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/test-tools.yml)
[![Update n8n version](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml/badge.svg)](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml)

## Docker container

Get a working container with N8N and the scanning tools:

1. Copy `n8n.env.default` to `n8n.env`, adjust variables if needed
2. Build image and start the container:

```shell
docker compose -p n8n-scanning up -d --build
```

Stop the container when done:

```shell
docker compose down
```

## Custom N8N nodes

See `./nodes` for all available custom (action) nodes. This includes one for retrieving IP ranges from CSPs and for the
popular scanning tools NMap, ZMap, and MASSCAN.

When you make changes, build and start the container again with the aforementioned command.