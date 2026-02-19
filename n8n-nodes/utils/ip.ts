export function getVersionFromPrefix(prefix: string) {
	if (prefix.includes(':')) {
		return 6;
	}
	return 4;
}

export function countIPsInPrefix(prefix: string): number {
	const parts = prefix.split('/');
	if (parts.length !== 2) return 0;

	const mask = Number(parts[1]);
	if (!Number.isInteger(mask)) return 0;

	const ipVersion = getVersionFromPrefix(prefix);
	if (ipVersion === 4) {
		if (mask < 0 || mask > 32) return 0;
		return 2 ** (32 - mask);
	}

	if (ipVersion === 6) {
		if (mask < 0 || mask > 128) return 0;
		return 2 ** (128 - mask);
	}

	return 0;
}
