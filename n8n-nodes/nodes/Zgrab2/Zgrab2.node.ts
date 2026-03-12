import { IExecuteFunctions, INodeType, INodeTypeDescription } from 'n8n-workflow';
import { writeDataFile } from '../../utils/file';
import {
	createNotice,
	executeTool,
	getParams,
	ScannerDescription,
	ScannerProperties,
} from '../ScannerBase';

const DEFAULT_INI = `# zgrab2 multiple configuration
# Add one section per module, e.g.:
[http]
port = 80
name = http
`;

// noinspection JSUnusedGlobalSymbols, referred in package.json
export class Zgrab2 implements INodeType {
	description: INodeTypeDescription = {
		...ScannerDescription,
		usableAsTool: true,
		displayName: 'ZGrab2',
		name: 'zgrab2',
		icon: 'file:zgrab2.svg', // Converted from https://github.com/zmap/graphics/blob/master/zmap1.pdf
		description: 'Perform application-layer scans with ZGrab2 using the "multiple" subcommand',
		defaults: {
			name: 'ZGrab2',
		},
		properties: [
			createNotice('https://github.com/zmap/zgrab2#multiple-module-usage'),
			{
				...ScannerProperties.commandOptions,
				placeholder: '--input-file targets.txt --blocklist-file /files/blocklist.txt',
				description:
					'Additional options to pass to <code>zgrab2 multiple</code>, e.g. <code>--input-file</code> and <code>--blocklist-file</code>',
			},
			{
				displayName: 'Config File (.ini)',
				name: 'configFileContent',
				type: 'string',
				typeOptions: {
					rows: 12,
				},
				default: DEFAULT_INI,
				description:
					'INI configuration passed to <code>zgrab2 multiple</code> via <code>--config-file</code>. The content is written to a temporary file at run time.',
				noDataExpression: false,
			},
		],
	};

	async execute(this: IExecuteFunctions) {
		const { cmdOptions } = getParams(this);
		const configFileContent = this.getNodeParameter('configFileContent', 0, '') as string;

		const jsonOutputFile = await writeDataFile('', 'zgrab2-output', 'json');
		const iniFile = await writeDataFile(configFileContent, 'zgrab2-config', 'ini');

		const command = `zgrab2 multiple --config-file ${iniFile} --output-file ${jsonOutputFile} ${cmdOptions}`;
		return executeTool(this, command, jsonOutputFile);
	}
}
