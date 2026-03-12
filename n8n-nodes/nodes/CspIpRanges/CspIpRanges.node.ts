import { readFile } from 'fs/promises';
import {
	IExecuteFunctions,
	INodeType,
	INodeTypeDescription,
	NodeConnectionTypes,
} from 'n8n-workflow';
import { countIPsInPrefix, getVersionFromPrefix } from '../../utils/ip';
import { CSP_OPTIONS, type CSPValue, getIpRangesFromRepo, type PrefixData } from './csp';
import { writeDataFile } from '../../utils/file';

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
		// Include a second file output, its filename can then easily be used in scanner CLI option via {{ $json.filePath }}
		outputs: [NodeConnectionTypes.Main, NodeConnectionTypes.Main],
		outputNames: ['Targets', 'Target File'],
		usableAsTool: true,
		properties: [
			{
				displayName: 'Cloud Service Providers',
				name: 'CSPs',
				type: 'multiOptions',
				options: [...CSP_OPTIONS],
				default: [],
			},
			{
				displayName: 'IP Version',
				name: 'ipVersion',
				type: 'multiOptions',
				options: [
					{ name: 'IPv4', value: 4 },
					{ name: 'IPv6', value: 6 },
				],
				default: [4, 6],
				description: 'Which IP versions to include in the output',
			},
			{
				displayName: 'Include Metadata',
				name: 'includeMetadata',
				type: 'boolean',
				default: false, // Having less data in the workflow is better for performance
				description:
					'Whether to include CSP-provided metadata (region, service, country code, etc.) on each item',
			},
			{
				displayName: 'Data Date',
				name: 'dataDate',
				type: 'string',
				default: '',
				placeholder: 'YYYY-MM-DD',
				description:
					'Date (YYYY-MM-DD) of the IP ranges snapshot to fetch. Leave empty to use today\'s date. Available snapshots: <a href="https://github.com/cpAdm/csp-ip-ranges/tree/main/data" target="_blank">cpAdm/csp-ip-ranges</a>',
			},
		],
	};

	async execute(this: IExecuteFunctions) {
		const providers = this.getNodeParameter('CSPs', 0) as CSPValue[];
		const ipVersions = this.getNodeParameter('ipVersion', 0) as number[];
		const includeMetadata = this.getNodeParameter('includeMetadata', 0) as boolean;
		const dateParam = (this.getNodeParameter('dataDate', 0) as string).trim();
		const date = dateParam || new Date().toISOString().split('T')[0]; // YYYY-MM-DD

		const allPrefixes = await getIpRangesFromRepo(this, date, providers);

		const result: PrefixDataWithCount[] = allPrefixes
			.map(
				(value): PrefixDataWithCount => ({
					...value,
					ipsInPrefix: countIPsInPrefix(value.ipPrefix),
					ipVersion: getVersionFromPrefix(value.ipPrefix),
				}),
			)
			.filter((entry) => ipVersions.includes(entry.ipVersion));

		// Build the target file content: one IP prefix per line for --input-file scanner options
		const prefixLines = result.map((e) => e.ipPrefix).join('\n');
		const filePath = await writeDataFile(prefixLines, 'csp-ip-ranges', 'txt');
		const fileBuffer = await readFile(filePath);
		const binaryData = await this.helpers.prepareBinaryData(fileBuffer, filePath, 'text/plain');
		const fileItem = {
			json: { filePath, lineCount: result.length },
			binary: { data: binaryData },
		};

		if (includeMetadata) {
			return [this.helpers.returnJsonArray(result), [fileItem]];
		}

		const stripped: Omit<PrefixDataWithCount, 'meta'>[] = result.map(
			({ csp, ipPrefix, ipsInPrefix, ipVersion }) => ({
				csp,
				ipPrefix,
				ipsInPrefix,
				ipVersion,
			}),
		);

		return [this.helpers.returnJsonArray(stripped), [fileItem]];
	}
}
