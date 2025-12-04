import os from 'node:os';
import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';
import * as fs from 'node:fs/promises';
import { emptyReturnData, execPromiseInTmp } from '../../utils/command';
import { parsesJSONLines, writeTempFile } from '../../utils/file';
import { getParams, ScannerDescription, ScannerProperties } from '../ScannerBase';

// noinspection JSUnusedGlobalSymbols, refered in package.json
export class Zmap implements INodeType {
	description: INodeTypeDescription = {
		...ScannerDescription,
		usableAsTool: true,
		displayName: 'ZMap',
		name: 'zmap',
		icon: 'file:zmap.svg', // Converted from https://github.com/zmap/graphics/blob/master/zmap1.pdf
		description: 'Perform scans with the network scanner ZMap',
		defaults: {
			name: 'ZMap',
		},
		properties: [
			ScannerProperties.notice,
			{
				...ScannerProperties.commandOptions,
				placeholder: '-p 80',
				description: "Additional options to pass to 'ZMap'",
			},
			ScannerProperties.targetKey,
			ScannerProperties.excludedTargetKey,
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const { isWorkflowActive, cmdOptions, targets, excludedTargets } = getParams(this);

		// TODO Find suitable data format
		const result = [];

		const jsonOutputFile = await writeTempFile('', 'json');
		const targetFile = await writeTempFile(targets.join(os.EOL), 'txt');
		const excludedTargetsFile = await writeTempFile(excludedTargets.join(os.EOL), 'txt');

		let res = emptyReturnData();
		let data = [];
		if (isWorkflowActive) {
			// TODO Use '--list-of-ips-file' instead of '--allowlist-file' when there are 1M IPs - but that does require IP's not CIDRs!
			const command = `zmap ${cmdOptions} --output-module=json -o ${jsonOutputFile} --allowlist-file ${targetFile} --blocklist-file ${excludedTargetsFile} --output-filter="success=1 && repeat=0"`;
			this.sendMessageToUI(command); // Debug via F12
			res = await execPromiseInTmp(command);
			if (res.exitCode !== 0) {
				throw new NodeOperationError(this.getNode(), `ZMap exited with code ${res.exitCode}`, {
					description: res.stderr,
				});
			}

			const fileData = await fs.readFile(jsonOutputFile, { encoding: 'utf8' });
			// Structure based on fields specified via '-f' or '--output-fields' in the cmdOptions
			data = parsesJSONLines(fileData);
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
