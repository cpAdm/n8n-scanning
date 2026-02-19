import {
	IExecuteFunctions,
	INodeType,
	INodeTypeDescription,
	NodeConnectionTypes,
	NodeOperationError,
} from 'n8n-workflow';
import { countIPsInPrefix, getVersionFromPrefix } from '../../utils/ip';
import { CSP_OPTIONS, type CSPValue, getIpRangesForCSP, type PrefixData } from './csp';

// TODO Add tests

type PrefixDataWithCount = PrefixData & {
	ipsInPrefix: number;
	ipVersion: 4 | 6;
};

// noinspection JSUnusedGlobalSymbols, refered in package.json
export class CspIpRanges implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'IP Ranges: CSPs',
		name: 'cspIpRanges',
		icon: 'file:cloud-download.svg',
		group: ['input'],
		version: 1, // Should be in sync with the node.json file
		description: 'Retrieve the IP ranges from the selected CSPs',
		defaults: {
			name: 'IP Ranges: CSPs',
		},
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

	async execute(this: IExecuteFunctions) {
		const providers = this.getNodeParameter('CSPs', 0) as string[];
		const result: PrefixDataWithCount[] = [];

		for (const provider of providers) {
			const data = await getIpRangesForCSP(this, provider as CSPValue);
			if (data === null) {
				throw new NodeOperationError(this.getNode(), 'Invalid CSP', {
					description: `Found unsupported CSP: '${provider}'`,
				});
			}

			// Note that summation of prefixes is not necessarily actual total - there might be overlapping prefixes
			const prefixData = data.map(
				(value) =>
					({
						...value,
						ipsInPrefix: countIPsInPrefix(value.ipPrefix),
						ipVersion: getVersionFromPrefix(value.ipPrefix),
					}) as const,
			);

			result.push(...prefixData);
		}

		return [this.helpers.returnJsonArray(result)];
	}
}
