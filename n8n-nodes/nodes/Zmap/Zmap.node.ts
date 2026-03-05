import { IExecuteFunctions, INodeType, INodeTypeDescription } from 'n8n-workflow';
import { writeDataFile } from '../../utils/file';
import { executeTool, getParams, ScannerDescription, ScannerProperties } from '../ScannerBase';

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
				placeholder:
					'--allowlist-file targets.txt --blocklist-file blocklist.txt --output-filter="success=1 && repeat=0" -p 80',
				description: "Additional options to pass to 'ZMap'",
			},
		],
	};

	async execute(this: IExecuteFunctions) {
		const { cmdOptions } = getParams(this);
		const jsonOutputFile = await writeDataFile('', 'zmap-output', 'json');
		const command = `zmap ${cmdOptions} --output-module=json -o ${jsonOutputFile}`;
		return executeTool(this, command, jsonOutputFile);
	}
}
