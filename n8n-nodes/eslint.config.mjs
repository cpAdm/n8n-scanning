import { configWithoutCloudSupport } from '@n8n/node-cli/eslint';

// Importing Node.js modules is not allowed with strict config, but we need to execute commands.
// This does mean that we cannot publish our nodes on n8n cloud and strict mode is set to "false".
export default configWithoutCloudSupport;
