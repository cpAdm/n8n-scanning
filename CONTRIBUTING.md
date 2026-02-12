# Contributing

## Updating n8n

This repro has an [GitHub workflow](https://github.com/cpAdm/n8n-scanning/actions/workflows/update-n8n.yml) that checks
daily if the docker image has an oudated n8n version. It will create a PR for this update. Run the other testing
pipelines on this branch before merging it.

## Tips for Remote development

When using WebStorm, you can use a remote host to deploy to. Do exclude all build folders like `node_modules` and `dist`
to limit the amount of files that need to be transferred. 