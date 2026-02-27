import os from 'node:os';
import {
	IExecuteFunctions,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';
import { emptyReturnData, execPromise } from '../../utils/command';
import { parseJSONFile, writeDataFile } from '../../utils/file';
import { getParams, ScannerDescription, ScannerProperties } from '../ScannerBase';

// noinspection JSUnusedGlobalSymbols, refered in package.json
export class Masscan implements INodeType {
	description: INodeTypeDescription = {
		...ScannerDescription,
		usableAsTool: true,
		displayName: 'MASSCAN',
		name: 'masscan',
		icon: 'file:masscan.svg', // Copied from https://www.kali.org/tools/masscan/images/masscan-logo.svg
		description: 'Perform scans with the network scanner MASSCAN',
		defaults: {
			name: 'MASSCAN',
		},
		properties: [
			ScannerProperties.notice,
			{
				...ScannerProperties.commandOptions,
				placeholder: '-p 80',
				description: "Additional options to pass to 'MASSCAN'",
			},
			ScannerProperties.targetKey,
			ScannerProperties.excludedTargetKey,
		],
	};

	async execute(this: IExecuteFunctions) {
		const { isWorkflowActive, cmdOptions, targets, excludedTargets } = getParams(this);

		const jsonOutputFile = await writeDataFile('', 'masscan-output', 'json');
		const targetFile = await writeDataFile(targets.join(os.EOL), 'masscan-targets', 'txt');
		const excludedTargetsFile = await writeDataFile(
			excludedTargets.join(os.EOL),
			'masscan-excluded-targets',
			'txt',
		);

		const command = `masscan ${cmdOptions} -oJ ${jsonOutputFile} --includefile ${targetFile} --excludefile ${excludedTargetsFile}`;
		let res = emptyReturnData();
		let data = [];
		if (isWorkflowActive) {
			res = await execPromise(command);
			if (res.exitCode !== 0) {
				throw new NodeOperationError(this.getNode(), `masscan exited with code ${res.exitCode}`, {
					description: res.stderr,
				});
			}

			data = await parseJSONFile(jsonOutputFile);
		}

		return [
			this.helpers.returnJsonArray(data),
			this.helpers.returnJsonArray({
				command: command,
				stdout: res.stdout,
			}),
		];
	}
}
