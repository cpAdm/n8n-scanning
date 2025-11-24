import os from 'node:os';
import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeConnectionTypes } from 'n8n-workflow';
import * as fs from 'node:fs/promises';
import { emptyReturnData, execPromiseInTmp } from '../../utils/command';
import { writeTempFile } from '../../utils/file';

export class Zmap implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'ZMap',
		name: 'zmap',
		icon: 'file:zmap.svg', // Converted from https://github.com/zmap/graphics/blob/master/zmap1.pdf
		group: ['transform'],
		version: 1, // Should be in sync with the node.json file
		description: 'Perform scans with the network scanner ZMap',
		defaults: {
			name: 'ZMap',
		},
		inputs: [NodeConnectionTypes.Main],
		outputs: [NodeConnectionTypes.Main],
		usableAsTool: true,
		properties: [
			{
				displayName:
					'Use with caution, only use trusted inputs!<br><br>If the workflow is inactive, this node will return fake data.',
				name: 'notice',
				type: 'notice',
				default: '',
			},
			{
				displayName: 'Command Options',
				name: 'cmdOptions',
				type: 'string',
				default: '',
				placeholder: '-p 80',
				description: 'Additional options to pass to `ZMap`',
			},
			{
				displayName: 'Target List',
				required: true,
				name: 'targets',
				type: 'multiOptions',
				allowArbitraryValues: true,
				validateType: 'array',
				default: [],
				description: 'List of subnets to constrain scan to, in CIDR notation, e.g. 192.168.0.0/16',
			},
			{
				displayName: 'Excluded Target List',
				name: 'excludedTargets',
				type: 'multiOptions',
				allowArbitraryValues: true,
				validateType: 'array',
				default: [],
				description: 'List of subnets to exclude, in CIDR notation, e.g. 192.168.0.0/16',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const isWorkflowActive = this.getWorkflow().active;

		// TODO verify parameter types
		const cmdOptions = this.getNodeParameter('cmdOptions', 0, '') as string;
		const targets = this.getNodeParameter('targets', 0, []) as string[];
		const excludedTargets = this.getNodeParameter('excludedTargets', 0, []) as string[];

		// TODO Find suitable data format
		const result = [];

		const jsonOutputFile = await writeTempFile('', 'json');
		const targetFile = await writeTempFile(targets.join(os.EOL), 'txt');
		const excludedTargetsFile = await writeTempFile(excludedTargets.join(os.EOL), 'txt');

		let res = emptyReturnData();
		let data = [];
		if (isWorkflowActive) {
			res = await execPromiseInTmp(
				`zmap ${cmdOptions} --output-module=json -o ${jsonOutputFile} --list-of-ips-file ${targetFile} --blocklist-file ${excludedTargetsFile}`,
			);
			const fileData = await fs.readFile(jsonOutputFile, { encoding: 'utf8' });
			data = fileData.split('\n').map((el) => JSON.parse(el));
		} else {
			// TODO return dummy data
		}

		result.push({
			active: isWorkflowActive,
			output: res,
			targets: targets,
			data: data,
		});

		return [this.helpers.returnJsonArray(result)];
	}
}
