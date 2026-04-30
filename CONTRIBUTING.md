# Contributing

## Directory Structure

Here's a quick overview of the main directories:
- `data/` – Where output data (such as `.json` results, `.png` analysis plots) and the `blocklist.txt` are stored.
- `n8n-nodes/` – The TypeScript source code for the custom n8n scanning nodes (e.g., Nmap, Masscan, Zmap, Zgrab2).
- `scripts/` – Python scripts to parse, analyze, and plot the scanning results.
- `tests/` – E2E tests for the scanning n8n workflows.
- `traefik/` – Configuration files for the Traefik reverse proxy.
- `web/` / `web-template/` – HTML/CSS setup for the responsible contact page hosted by the container.

## Commits

This repro is following [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/).

## Updating n8n

This repro has an [GitHub workflow](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml) that checks
daily if the docker image has an oudated n8n version. It will create a PR for this update. Run the other testing
pipelines on this branch before merging it.

## Testing

[//]: # (TODO Add more tests, e.g. unit tests for the custom nodes, more E2E tests, ...)

Currently, there is limited testing in place:

- The custom nodes are checked for TypeScript and Lint errors in the CI pipelines
- CI pipelines do check if the container has the tools available
- A simple E2E workflow test with Nmap node can be found in `tests` folder

## Tips for Remote development

When using WebStorm, you can use a remote host to deploy to. Do exclude all build folders like `node_modules` and `dist`
to limit the amount of files that need to be transferred.
