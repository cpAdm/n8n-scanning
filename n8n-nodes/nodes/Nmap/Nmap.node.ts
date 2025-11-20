import { exec } from 'child_process';
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
import { parseStringPromise } from 'xml2js';
import { EOL } from 'node:os';

interface IExecReturnData {
	exitCode: number;
	error?: Error;
	stderr: string;
	stdout: string;
}

function emptyReturnData(): IExecReturnData {
	return {
		error: undefined,
		exitCode: 0,
		stderr: '',
		stdout: '',
	};
}

// We leverage 'xml2js' (used by n8n) to convert the XML
function xmlToJson(xml: string) {
	return parseStringPromise(xml, { mergeAttrs: true, explicitArray: false });
}

/**
 * Promisifiy exec manually to also get the exit code
 * (copied from n8n's ExecuteCommand.node.ts)
 */
async function execPromise(cwd: string, command: string): Promise<IExecReturnData> {
	const returnData = emptyReturnData();

	return await new Promise((resolve) => {
		exec(command, { cwd: cwd }, (error, stdout, stderr) => {
			returnData.stdout = stdout.trim();
			returnData.stderr = stderr.trim();

			if (error) {
				returnData.error = error;
			}

			resolve(returnData);
		}).on('exit', (code) => {
			returnData.exitCode = code || 0;
		});
	});
}

export class Nmap implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Nmap',
		name: 'nmap',
		icon: 'file:nmap.svg', // Copied from https://nmap.org/images/nmap-logo-64px.svg
		group: ['transform'],
		version: 1, // Should be in sync with the node.json file
		description: 'Perform scans with the network scanner Nmap',
		defaults: {},
		inputs: [NodeConnectionTypes.Main],
		outputs: [NodeConnectionTypes.Main],
		usableAsTool: true,
		properties: [
			{
				displayName: 'Use with caution. Only use trusted inputs to prevent cmd injection.',
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
					'List of hosts to scan.\nEntries can be in any of the formats accepted by Nmap',
			},
			{
				displayName: 'Excluded Target List',
				name: 'excludedTargets',
				type: 'multiOptions',
				allowArbitraryValues: true,
				validateType: 'array',
				default: [],
				description:
					'List of hosts to be excluded from the scan.\nEntries can be in any of the formats accepted by Nmap',
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

		const xmlOutputFilename = 'scan.xml';
		const targetFilename = 'target_list.txt';
		const excludedTargetsFilename = 'excluded_target_list.txt';
		await fs.writeFile(path.join(cwd, targetFilename), targets.join(EOL));
		await fs.writeFile(path.join(cwd, excludedTargetsFilename), excludedTargets.join(EOL));

		let res;
		if (isWorkflowActive) {
			res = await execPromise(
				cwd,
				`nmap ${cmdOptions} -oX ${xmlOutputFilename} -iL ${targetFilename} --excludefile ${excludedTargetsFilename}`,
			);
		} else {
			res = emptyReturnData();
		}

		const fileData = await fs.readFile(path.join(cwd, xmlOutputFilename), { encoding: 'utf8' });
		const xmlData = fileData.replace(/(\r\n|\n|\r)/gm, ''); // TODO find nicer solution
		result.push({
			active: isWorkflowActive,
			ouput: res,
			targets: targets,
			data: (await xmlToJson(xmlData)) as object,
		});

		return [this.helpers.returnJsonArray(await Promise.all(result))];
	}
}
