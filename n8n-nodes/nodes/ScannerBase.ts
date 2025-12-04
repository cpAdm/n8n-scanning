import {
	type IExecuteFunctions,
	INodeProperties,
	INodeTypeDescription,
	NodeConnectionTypes,
	NodeOperationError,
} from 'n8n-workflow';
import get from 'lodash/get';

export const ScannerDescription = {
	group: ['transform'],
	version: 1, // Should be in sync with the node.json file
	inputs: [NodeConnectionTypes.Main, NodeConnectionTypes.Main],
	inputNames: ['Targets', 'Excluded targets'],
	requiredInputs: [0],
	// TODO Optionally we can have multiple outputs, e.g. 1 for raw (streamed) cmd output data, other for processed data?
	outputs: [NodeConnectionTypes.Main],
} satisfies Partial<INodeTypeDescription>;

export const ScannerProperties = {
	notice: {
		displayName:
			'Use with caution, only use trusted inputs!<br><br>If the workflow is inactive, this node will not call the scanner.',
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
	// Inspired by: https://github.com/n8n-io/n8n/blob/master/packages/nodes-base/nodes/CompareDatasets/CompareDatasets.node.ts
	targetKey: {
		displayName: 'Target Key',
		required: true,
		name: 'targetKey',
		type: 'string',
		default: 'ipPrefix',
		allowArbitraryValues: false,
		requiresDataPath: 'single', // Ability to drag field from the input in UI to this input
		description: "Key in the 'Targets' input entries that is the IP Prefix (in CIDR notation)",
	},
	excludedTargetKey: {
		displayName: 'Excluded Target Key',
		name: 'excludedTargetKey',
		type: 'string',
		default: 'ipPrefix',
		allowArbitraryValues: false,
		requiresDataPath: 'single',
		description:
			"Key in the 'Excluded targets' input entries that is the IP Prefix (in CIDR notation)",
	},
} satisfies Record<string, INodeProperties>;

export function getParams(functions: IExecuteFunctions) {
	const isWorkflowActive = functions.getWorkflow().active;
	const targetInput = functions.getInputData(0);
	const excludedTargetInput = functions.getInputData(1);

	// TODO verify parameters
	const cmdOptions = functions.getNodeParameter('cmdOptions', 0, '') as string;
	const targetKey = functions.getNodeParameter('targetKey', 0, []) as string;
	const excludedTargetKey = functions.getNodeParameter('excludedTargetKey', 0, []) as string;

	const targets = targetInput.map((input) => get(input.json, targetKey)).filter(Boolean);
	if (targets.length === 0) {
		throw new NodeOperationError(functions.getNode(), 'No targets found', {
			description: `Check if Target Key "${targetKey}" is correct. `,
		});
	}

	const excludedTargets = excludedTargetKey
		? excludedTargetInput.map((input) => get(input.json, excludedTargetKey)).filter(Boolean)
		: [];

	return {
		isWorkflowActive,
		cmdOptions,
		targets,
		excludedTargets,
	};
}
