import path from 'node:path';
import fs from 'node:fs/promises';

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
