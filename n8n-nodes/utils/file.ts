import path from 'node:path';
import fs from 'node:fs/promises';
import { parseStringPromise } from 'xml2js';

/** This is the dir name as defined in the volumes in the docker n8n service */
export const SHARED_DIR = '/files';

/** @return The file path that was written to */
export async function writeDataFile(
	contents: string,
	name: string,
	suffix: 'txt' | 'json' | 'xml',
) {
	const timePart = new Date().toISOString().replace(/[:.]/g, '-');
	const fileName = `${timePart}-${name}.${suffix}`;
	const filePath = path.join(SHARED_DIR, fileName);

	await fs.writeFile(filePath, contents);

	return filePath;
}

export async function parseJSONFile(filePath: string) {
	const fileData = await fs.readFile(filePath, { encoding: 'utf8' });
	return JSON.parse(fileData);
}

export async function parseJSONLFile(filePath: string) {
	const fileData = await fs.readFile(filePath, { encoding: 'utf8' });
	return fileData
		.split('\n')
		.filter(Boolean) // ignore empty rows
		.map((el) => JSON.parse(el));
}

// We leverage 'xml2js' (used by n8n) to convert the XML
function xmlToJson(xml: string) {
	return parseStringPromise(xml, { mergeAttrs: true, explicitArray: false });
}

export async function parseXMLFile(filePath: string) {
	const fileData = await fs.readFile(filePath, { encoding: 'utf8' });
	const xmlData = fileData.replace(/(\r\n|\n|\r)/gm, ''); // TODO find nicer solution
	return await xmlToJson(xmlData);
}
