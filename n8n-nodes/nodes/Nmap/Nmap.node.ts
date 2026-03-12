import { IExecuteFunctions, INodeType, INodeTypeDescription } from 'n8n-workflow';
import { writeDataFile } from '../../utils/file';
import { createNotice, executeTool, getParams, ScannerDescription, ScannerProperties } from '../ScannerBase';

// noinspection JSUnusedGlobalSymbols, refered in package.json
export class Nmap implements INodeType {
	description: INodeTypeDescription = {
		...ScannerDescription,
		usableAsTool: true,
		displayName: 'Nmap',
		name: 'nmap',
		icon: 'file:nmap.svg', // Copied from https://nmap.org/images/nmap-logo-64px.svg
		description: 'Perform scans with the network scanner Nmap',
		defaults: {
			name: 'Nmap',
		},
		properties: [
			createNotice('https://nmap.org/book/man-briefoptions.html'),
			{
				...ScannerProperties.commandOptions,
				placeholder: '-iL targets.txt --excludefile  /files/blocklist.txt -sn ',
				description: "Additional options to pass to 'Nmap'",
			},
		],
	};

	async execute(this: IExecuteFunctions) {
		const { cmdOptions } = getParams(this);
		const xmlOutputFile = await writeDataFile('', 'nmap-output', 'xml');
		const command = `nmap ${cmdOptions} -oX ${xmlOutputFile}`;
		return executeTool(this, command, xmlOutputFile);
	}
}
