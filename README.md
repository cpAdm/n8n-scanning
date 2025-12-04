# N8N Scanning

## Docker container

Get a working container with N8N and the scanning tools.

Build container:
```shell
docker build -t cpadm:n8n .
```

Start container:
```shell
docker compose -p n8n-scanning up -d
```

Stop container
```shell
docker compose down
```


## Custom N8N nodes

See `./nodes` for all available custom (action) nodes. This includes one for retrieving IP ranges from CSPs and for the
popular scanning tools NMap, ZMap, and MASSCAN.