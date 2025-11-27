import os from 'os';
import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import { NodeConnectionTypes } from 'n8n-workflow';
import * as fs from 'node:fs/promises';
import { parseStringPromise } from 'xml2js';
import { emptyReturnData, execPromiseInTmp } from '../../utils/command';
import { writeTempFile } from '../../utils/file';

// We leverage 'xml2js' (used by n8n) to convert the XML
function xmlToJson(xml: string) {
	return parseStringPromise(xml, { mergeAttrs: true, explicitArray: false });
}

export class Nmap implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Nmap',
		name: 'nmap',
		icon: 'file:nmap.svg', // Copied from https://nmap.org/images/nmap-logo-64px.svg
		group: ['transform'],
		version: 1, // Should be in sync with the node.json file
		description: 'Perform scans with the network scanner Nmap',
		defaults: {
			name: 'Nmap',
		},
		inputs: [NodeConnectionTypes.Main],
		outputs: [NodeConnectionTypes.Main],
		usableAsTool: true,
		properties: [
			{
				displayName:
					'Use with caution, only use trusted inputs!<br><br>If the workflow is inactive, this node will not call the scanner.',
				name: 'notice',
				type: 'notice',
				default: '',
			},
			{
				displayName: 'Command Options',
				name: 'cmdOptions',
				type: 'string',
				default: '',
				placeholder: '-sn',
				description: 'Additional options to pass to `Nmap`',
			},
			{
				displayName: 'Target List',
				required: true,
				name: 'targets',
				type: 'multiOptions',
				allowArbitraryValues: true,
				validateType: 'array',
				default: [],
				description:
					'List of hosts to scan.<br><br>Entries can be in any of the formats accepted by Nmap',
			},
			{
				displayName: 'Excluded Target List',
				name: 'excludedTargets',
				type: 'multiOptions',
				allowArbitraryValues: true,
				validateType: 'array',
				default: [],
				description:
					'List of hosts to be excluded from the scan.<br><br> Entries can be in any of the formats accepted by Nmap',
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

		const xmlOutputFile = await writeTempFile('', 'xml');
		const targetFile = await writeTempFile(targets.join(os.EOL), 'txt');
		const excludedTargetsFile = await writeTempFile(excludedTargets.join(os.EOL), 'txt');

		let res = emptyReturnData();
		let data = {};
		if (isWorkflowActive) {
			res = await execPromiseInTmp(
				`nmap ${cmdOptions} -oX ${xmlOutputFile} -iL ${targetFile} --excludefile ${excludedTargetsFile}`,
			);
			const fileData = await fs.readFile(xmlOutputFile, { encoding: 'utf8' });
			const xmlData = fileData.replace(/(\r\n|\n|\r)/gm, ''); // TODO find nicer solution
			data = (await xmlToJson(xmlData)) as object;
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
