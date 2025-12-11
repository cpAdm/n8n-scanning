import { randomBytes } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs/promises';
import { parseStringPromise } from 'xml2js';

const TMP_DIR = os.tmpdir();

/** @return The file path that was written to */
export async function writeTempFile(contents: string, suffix: 'txt' | 'json' | 'xml') {
	const fileName = randomBytes(16).toString('hex') + suffix;
	const filePath = path.join(TMP_DIR, fileName);

	await fs.writeFile(filePath, contents);

	return filePath;
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
