import {
	type IExecuteFunctions,
	INodeProperties,
	INodeTypeDescription,
	NodeConnectionTypes,
	NodeOperationError,
} from 'n8n-workflow';
import { emptyReturnData, execPromise } from '../utils/command';

export const ScannerDescription = {
	group: ['transform'],
	version: 1, // Should be in sync with the node.json file
	inputs: [NodeConnectionTypes.Main],
	requiredInputs: [0],
	outputs: [NodeConnectionTypes.Main],
	outputNames: ['Output'],
} satisfies Partial<INodeTypeDescription>;

export function createNotice(docUrl: string): INodeProperties {
	return {
		// Not all HTML elements are allowed here: https://github.com/n8n-io/n8n/blob/b97e864f93ec51246639f582e7c9788d0bc12d1a/packages/frontend/%40n8n/design-system/src/components/N8nNotice/Notice.vue#L46C3-L46C34
		displayName: `
			<ul>
					<li>Use with caution, only use trusted inputs!</li>
					<li>Scanner is skipped in inactive workflows — activate before running</li>
					<li><a href="${docUrl}" target="_blank">View scanner documentation ↗</a></li>
			</ul>`,
		name: 'notice',
		type: 'notice',
		default: '',
	};
}

export const ScannerProperties = {
	// TODO Add note that output file will automatically be generated
	commandOptions: {
		displayName: 'Command Options',
		name: 'cmdOptions',
		type: 'string',
		default: '',
	},
} satisfies Record<string, INodeProperties>;

export function getParams(functions: IExecuteFunctions) {
	const cmdOptions = functions.getNodeParameter('cmdOptions', 0, '') as string;
	return {
		cmdOptions,
	};
}

export async function executeTool(
	functions: IExecuteFunctions,
	command: string,
	outputFile: string,
) {
	let res = emptyReturnData();
	if (functions.getWorkflow().active) {
		res = await execPromise(command);
		if (res.exitCode !== 0) {
			throw new NodeOperationError(functions.getNode(), `Exited with code ${res.exitCode}`, {
				description: res.stderr,
			});
		}
	}

	return [
		functions.helpers.returnJsonArray({
			...res,
			command: command,
			outputFile: outputFile,
		}),
	];
}
