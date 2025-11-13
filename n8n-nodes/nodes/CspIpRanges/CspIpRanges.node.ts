import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeConnectionTypes } from 'n8n-workflow';

const CSP_OPTIONS = [
	{
		name: 'Amazon Web Services',
		value: 'AWS',
	},
	{
		name: 'Microsoft Azure',
		value: 'azure',
	},
	{
		name: 'Google Cloud Platform',
		value: 'GCP',
	},
	{
		name: 'Cloudflare',
		value: 'cloudflare',
	},
	{
		name: 'IBM Cloud',
		value: 'IBM',
	},
] as const;
type CSPValue = (typeof CSP_OPTIONS)[number]['value'];

export class CspIpRanges implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'IP Ranges: CSPs',
		name: 'cspIpRanges',
		icon: { light: 'file:csp-ip-ranges.svg', dark: 'file:csp-ip-ranges.dark.svg' }, // TODO change
		group: ['input'],
		version: 1, // Should be in sync with the node.json file
		description: 'Retrieve the IP ranges from the selected CSPs',
		defaults: {},
		inputs: [NodeConnectionTypes.Main],
		outputs: [NodeConnectionTypes.Main],
		usableAsTool: true,
		properties: [
			{
				displayName: 'Cloud Service Providers',
				name: 'CSPs',
				type: 'multiOptions',
				options: [...CSP_OPTIONS],
				default: [],
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		// const items = this.getInputData();

		const providers = this.getNodeParameter('CSPs', 0) as CSPValue[];
		// TODO Find suitable data format
		const result = [];

		for (const provider of providers) {
			if (provider === 'GCP') {
				// Google: https://support.google.com/a/answer/10026322?hl=en-419
				const response = await this.helpers.httpRequest({
					method: 'GET',
					url: 'https://www.gstatic.com/ipranges/cloud.json',
				});
				result.push({
					[provider]: response,
				});
			}

			// TODO other CSP's

			// TODO error message if unknown
		}

		return [this.helpers.returnJsonArray(await Promise.all(result))];
	}
}
