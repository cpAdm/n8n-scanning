import os from 'os';
import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeConnectionTypes } from 'n8n-workflow';
import * as fs from 'node:fs/promises';
import path from 'node:path';
import { EOL } from 'node:os';
import { emptyReturnData, execPromise } from '../../utils/command';

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

		// We cannot use process.cwd() as current user does not have write permissions there
		const cwd = os.tmpdir();

		// TODO move to utils, and randomize file name since folder is shared?
		const jsonOutputFilename = 'scan.json';
		const targetFilename = 'target_list.txt';
		const excludedTargetsFilename = 'excluded_target_list.txt';
		await fs.writeFile(path.join(cwd, targetFilename), targets.join(EOL));
		await fs.writeFile(path.join(cwd, excludedTargetsFilename), excludedTargets.join(EOL));

		let res;
		if (isWorkflowActive) {
			res = await execPromise(
				cwd,
				`zmap ${cmdOptions} --output-module=json -o ${jsonOutputFilename} ---list-of-ips-file ${targetFilename} --blocklist-file ${excludedTargetsFilename}`,
			);
		} else {
			// TODO return dummy data
			res = emptyReturnData();
		}

		const fileData = await fs.readFile(path.join(cwd, jsonOutputFilename), { encoding: 'utf8' });
		result.push({
			active: isWorkflowActive,
			ouput: res,
			targets: targets,
			data: fileData.split('\n').map((el) => JSON.parse(el)),
		});

		return [this.helpers.returnJsonArray(await Promise.all(result))];
	}
}
