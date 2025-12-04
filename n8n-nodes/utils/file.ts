import { randomBytes } from 'node:crypto';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs/promises';

const TMP_DIR = os.tmpdir();

/** @return The file path that was written to */
export async function writeTempFile(contents: string, suffix: 'txt' | 'json' | 'xml') {
	const fileName = randomBytes(16).toString('hex') + suffix;
	const filePath = path.join(TMP_DIR, fileName);

	await fs.writeFile(filePath, contents);

	return filePath;
}

export function parsesJSONLines(fileData: string) {
	return fileData
		.split('\n')
		.filter(Boolean) // ignore empty rows
		.map((el) => JSON.parse(el));
}
