import { type IExecuteFunctions, NodeOperationError } from 'n8n-workflow';

// TODO other CSPs
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
	// TODO IBM is a bit more tricky. There is no JSON file, just the markdown of their documentation:
	// https://github.com/ibm-cloud-docs/infrastructure-hub/blob/master/ips.md
	// (we could maybe decouple this into a separate repo that updates daily?)
	// {
	// 	name: 'IBM Cloud',
	// 	value: 'IBM',
	// },
] as const;
export type CSPValue = (typeof CSP_OPTIONS)[number]['value'];

type AwsData = {
	syncToken: string;
	createDate: string;
	prefixes: {
		ip_prefix: string;
		region: string;
		service: string;
		network_border_group: string;
	}[];
	ipv6_prefixes: {
		ipv6_prefix: string;
		region: string;
		service: string;
		network_border_group: string;
	}[];
};

type GcpData = {
	syncToken: string;
	creationTime: string;
	prefixes: (
		| {
				ipv4Prefix: string;
				service: string;
				scope: string;
		  }
		| {
				ipv6Prefix: string;
				service: string;
				scope: string;
		  }
	)[];
};

type AzureData = {
	changeNumber: number;
	cloud: 'Public';
	values: {
		name: string;
		id: string;
		properties: {
			changeNumber: number;
			region: string;
			regionId: number;
			platform: string;
			systemService: string;
			addressPrefixes: string[];
			networkFeatures: string[] | null;
		};
	}[];
};

type CloudflareData = {
	result: {
		etag: string;
		ipv4_cidrs: string[];
		ipv6_cidrs: string[];
		jdcloud_cidrs: string[];
	};
	success: boolean;
	errors: unknown;
	messages: unknown;
};

export type PrefixData = {
	csp: CSPValue;
	ipPrefix: string;

	/** Any other information the CSP might provide */
	meta: Partial<{
		/** Also known as 'scope' */
		region: string;
		service: string;
		countryCode: string;
		subdivisionCode: string;
		city: string;
		postalCode: string;
	}>;
};

export async function getIpRangesForCSP(
	functions: IExecuteFunctions,
	provider: CSPValue,
): Promise<PrefixData[] | null> {
	// TODO Check for all providers if we retrieve all kind of service IP's. Maybe have this as additional node option?

	if (provider === 'GCP') {
		// https://support.google.com/a/answer/10026322?hl=en-419
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: 'https://www.gstatic.com/ipranges/cloud.json',
		})) as GcpData;

		return data.prefixes.map((entry) => ({
			csp: 'GCP',
			ipPrefix: 'ipv4Prefix' in entry ? entry.ipv4Prefix : entry.ipv6Prefix,
			meta: { region: entry.scope, service: entry.service },
		}));
	}

	if (provider === 'AWS') {
		// https://docs.aws.amazon.com/vpc/latest/userguide/aws-ip-ranges.html
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: 'https://ip-ranges.amazonaws.com/ip-ranges.json',
		})) as AwsData;

		const ipv4Data: PrefixData[] = data.prefixes.map((entry) => ({
			csp: 'AWS',
			ipPrefix: entry.ip_prefix,
			meta: { region: entry.region, service: entry.service },
		}));

		const ipv6Data: PrefixData[] = data.ipv6_prefixes.map((entry) => ({
			csp: 'AWS',
			ipPrefix: entry.ipv6_prefix,
			meta: { region: entry.region, service: entry.service },
		}));

		return [...ipv4Data, ...ipv6Data];
	}

	if (provider === 'azure') {
		// There is no public REST API, so find the newest download url via the website (changes weekly)
		// https://www.microsoft.com/en-us/download/details.aspx?id=56519

		const url = 'https://www.microsoft.com/en-us/download/details.aspx?id=56519';
		const pageHtml = (await functions.helpers.httpRequest({
			method: 'GET',
			url: url,
		})) as string;

		const jsonUrlMatch = pageHtml.match(
			/https:\/\/download\.microsoft\.com\/[^"]*ServiceTags_Public[^"]*\.json/,
		);
		if (!jsonUrlMatch) {
			throw new NodeOperationError(functions.getNode(), 'Azure link not found', {
				description: `Failed to find Azure ranges download link on ${url}`,
			});
		}

		const downloadUrl = jsonUrlMatch[0];
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: downloadUrl,
		})) as AzureData;

		const result: PrefixData[] = [];
		for (const entry of data.values) {
			for (const prefix of entry.properties.addressPrefixes) {
				result.push({
					csp: 'azure',
					ipPrefix: prefix,
					meta: { region: entry.properties.region, service: entry.name },
				});
			}
		}

		return result;
	}

	if (provider === 'cloudflare') {
		// https://www.cloudflare.com/ips/
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: 'https://api.cloudflare.com/client/v4/ips?networks=jdcloud',
		})) as CloudflareData;

		const result: PrefixData[] = [];
		data.result.ipv4_cidrs.forEach((prefix) =>
			result.push({
				csp: 'cloudflare',
				ipPrefix: prefix,
				meta: { service: 'CLOUDFLARE' },
			}),
		);
		data.result.ipv6_cidrs.forEach((prefix) =>
			result.push({
				csp: 'cloudflare',
				ipPrefix: prefix,
				meta: { service: 'CLOUDFLARE' },
			}),
		);
		data.result.jdcloud_cidrs.forEach((prefix) =>
			result.push({
				csp: 'cloudflare',
				ipPrefix: prefix,
				meta: { service: 'JD_CLOUD' },
			}),
		);

		return result;
	}

	if (provider === 'digital_ocean') {
		// https://ideas.digitalocean.com/documentation/p/list-of-digital-ocean-ips-cidrs
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: 'https://digitalocean.com/geo/google.csv',
		})) as string;

		// This is a CSV file with rows formatted as: <ip_prefix>,<country_code>,<subdivision_code>,<city>,<postal_code>
		const result: PrefixData[] = [];
		data.split('\n').forEach((rowRaw) => {
			const [ipPrefix, countryCode, subdivisionCode, city, postalCode] = rowRaw.split(',');
			result.push({
				csp: 'digital_ocean',
				ipPrefix: ipPrefix,
				meta: { countryCode, subdivisionCode, city, postalCode },
			});
		});

		return result;
	}

	provider satisfies never;

	return null;
}
