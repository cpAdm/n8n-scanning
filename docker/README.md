Build container:
```shell
docker build -t cpadm:n8n .
```


// TODO Move command to top-level package-json? Then also use that inside the test GitHub workflow?

Start container:
```shell
docker compose -p n8n-scanning up -d
```

Stop container
```shell
docker compose down
```
