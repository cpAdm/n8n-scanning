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
	inputs: [NodeConnectionTypes.Main, NodeConnectionTypes.Main],
	inputNames: ['Targets', 'Excluded targets'],
	requiredInputs: [0],
	outputs: [NodeConnectionTypes.Main],
	outputNames: ['Output'],
} satisfies Partial<INodeTypeDescription>;

export const ScannerProperties = {
	// TODO Add custom notice for each scanner to see what cmd options are available?
	notice: {
		displayName:
			'Use with caution, only use trusted inputs! <br><br>If the workflow is inactive, this node will not call the scanner.',
		name: 'notice',
		type: 'notice',
		default: '',
	},
	commandOptions: {
		displayName: 'Command Options',
		name: 'cmdOptions',
		type: 'string',
		default: '',
		// placeholder: '-sn',
		description: 'Additional options to pass to the scanner',
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
