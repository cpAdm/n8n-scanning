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
import { writeTempFile } from '../../utils/file';
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
			res = await execPromiseInTmp(
				`zmap ${cmdOptions} --output-module=json -o ${jsonOutputFile} --list-of-ips-file ${targetFile} --blocklist-file ${excludedTargetsFile}`,
			);
			if (res.exitCode !== 0) {
				throw new NodeOperationError(this.getNode(), `ZMap exited with code ${res.exitCode}`, {
					description: res.stderr,
				});
			}
			const fileData = await fs.readFile(jsonOutputFile, { encoding: 'utf8' });
			data = fileData.split('\n').map((el) => JSON.parse(el));
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
