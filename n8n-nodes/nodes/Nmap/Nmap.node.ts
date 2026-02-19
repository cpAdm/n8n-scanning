import os from 'os';
import {
	IExecuteFunctions,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';
import { emptyReturnData, execPromiseInTmp } from '../../utils/command';
import { parseXMLFile, writeTempFile } from '../../utils/file';
import { getParams, ScannerDescription, ScannerProperties } from '../ScannerBase';

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
			ScannerProperties.notice,
			{
				...ScannerProperties.commandOptions,
				placeholder: '-sn',
				description: "Additional options to pass to 'Nmap'",
			},
			ScannerProperties.targetKey,
			ScannerProperties.excludedTargetKey,
		],
	};

	async execute(this: IExecuteFunctions) {
		const { isWorkflowActive, cmdOptions, targets, excludedTargets } = getParams(this);

		const xmlOutputFile = await writeTempFile('', 'xml');
		const targetFile = await writeTempFile(targets.join(os.EOL), 'txt');
		const excludedTargetsFile = await writeTempFile(excludedTargets.join(os.EOL), 'txt');

		const command = `nmap ${cmdOptions} -oX ${xmlOutputFile} -iL ${targetFile} --excludefile ${excludedTargetsFile}`;
		let res = emptyReturnData();
		let data = {};
		if (isWorkflowActive) {
			res = await execPromiseInTmp(command);
			if (res.exitCode !== 0) {
				throw new NodeOperationError(this.getNode(), `Nmap exited with code ${res.exitCode}`, {
					description: res.stderr,
				});
			}
			// TODO Find suitable data format
			data = await parseXMLFile(xmlOutputFile);
		}

		// TODO Should we read the ip ranges from input, and link it the tool output?
		//  https://docs.n8n.io/integrations/creating-nodes/build/reference/paired-items/

		// TODO use prepareBinaryData instead for better performance?
		// See read/write n8n node for example on how to work with binary data
		// await this.helpers.prepareBinaryData(Buffer.from(JSON.stringify(result)), 'nmap.json');
		return [
			this.helpers.returnJsonArray(data),
			this.helpers.returnJsonArray({
				command: command,
				stdout: res.stdout,
			}),
		];
	}
}
