# N8N Scanning

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