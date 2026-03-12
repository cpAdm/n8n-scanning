import { IExecuteFunctions, INodeType, INodeTypeDescription } from 'n8n-workflow';
import { writeDataFile } from '../../utils/file';
import { createNotice, executeTool, getParams, ScannerDescription, ScannerProperties } from '../ScannerBase';

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
			createNotice('https://github.com/robertdavidgraham/masscan#usage'),
			{
				...ScannerProperties.commandOptions,
				placeholder: '--includefile targets.txt --excludefile blacklist.txt -p 80',
				description: "Additional options to pass to 'MASSCAN'",
			},
		],
	};

	async execute(this: IExecuteFunctions) {
		const { cmdOptions } = getParams(this);
		const jsonOutputFile = await writeDataFile('', 'masscan-output', 'json');
		const command = `masscan ${cmdOptions} -oJ ${jsonOutputFile}`;

		return executeTool(this, command, jsonOutputFile);
	}
}
