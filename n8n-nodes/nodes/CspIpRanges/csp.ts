import { type IExecuteFunctions } from 'n8n-workflow';

const REPO_BASE_URL = 'https://github.com/cpAdm/csp-ip-ranges/raw/refs/heads/main/data';

// IMPORTANT: Below constants and types should be in sync with the ones in the csp-ip-ranges repo
export const CSP_OPTIONS = [
	{
		name: 'Amazon Web Services',
		value: 'AWS',
	},
	{
		name: 'Microsoft Azure',
		value: 'azure',
	},
	{
		name: 'Google Cloud Platform',
		value: 'GCP',
	},
	{
		name: 'Cloudflare',
		value: 'cloudflare',
	},
	{
		name: 'Digital Ocean',
		value: 'digital_ocean',
	},
	{
		name: 'IBM Cloud',
		value: 'IBM',
	},
	{
		name: 'Oracle Cloud',
		value: 'oracle_cloud',
	},
	{
		// Choopa was acquired by Vultr
		name: 'Vultr',
		value: 'vultr',
	},
] as const;
export type CSPValue = (typeof CSP_OPTIONS)[number]['value'];

export type PrefixData = {
	csp: CSPValue;
	ipPrefix: string;
	meta: Record<string, unknown>;
};

type RepoData = {
	repositoryVersion: string;
	timestamp: string;
	totalPrefixes: number;
	successCount: number;
	failureCount: number;
	failed: { provider: string; error: string }[];
	prefixes: {
		csp: CSPValue;
		ipPrefix: string;
		meta: PrefixData['meta'];
	}[];
};

export async function getIpRangesFromRepo(
	functions: IExecuteFunctions,
	date: string,
	providers: CSPValue[],
): Promise<PrefixData[]> {
	const data = (await functions.helpers.httpRequest({
		method: 'GET',
		url: `${REPO_BASE_URL}/${date}.json`,
	})) as RepoData;

	return data.prefixes
		.filter((entry) => providers.includes(entry.csp))
		.map((entry) => ({
			csp: entry.csp,
			ipPrefix: entry.ipPrefix,
			meta: entry.meta,
		}));
}
