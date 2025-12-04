import os from 'os';
import type {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
} from 'n8n-workflow';
import * as fs from 'node:fs/promises';
import { parseStringPromise } from 'xml2js';
import { emptyReturnData, execPromiseInTmp } from '../../utils/command';
import { writeTempFile } from '../../utils/file';
import { getParams, ScannerDescription, ScannerProperties } from '../ScannerBase';

// We leverage 'xml2js' (used by n8n) to convert the XML
function xmlToJson(xml: string) {
	return parseStringPromise(xml, { mergeAttrs: true, explicitArray: false });
}

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

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const { isWorkflowActive, cmdOptions, targets, excludedTargets } = getParams(this);

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

		// TODO Should we read the ip ranges from input, and link it the tool output?
		//  https://docs.n8n.io/integrations/creating-nodes/build/reference/paired-items/

		// TODO use prepareBinaryData instead for better performance?
		// await this.helpers.prepareBinaryData(Buffer.from(JSON.stringify(result)), 'nmap.json');
		return [this.helpers.returnJsonArray(result)];
	}
}
