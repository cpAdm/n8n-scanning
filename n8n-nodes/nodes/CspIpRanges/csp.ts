import { type IExecuteFunctions, NodeOperationError } from 'n8n-workflow';

// Matches IPv4: x.x.x.x/xx or IPv6: x:x:x:x:x:x:x:x/xx
const CIDR_REGEX = /([0-9a-f.:]+\/\d+)/gi;

// TODO (we maybe should decouple this into a separate repo that updates daily? - with JSON schema)

// TODO Not implemented for these providers:
// - Alibaba Cloud, does not publish its ranges, but we could pull prefixes from BGP for AS45102
// - OVH Cloud, IP ranges spreadout trough its documenation: https://help.ovhcloud.com/csm/en-gb-search?id=kb_search&query=List%20of%20IP&language=en
// - Tencent Cloud, does not publish is ranges
// - Rackspace, does not publish is ranges
// - Apache, does not publish is ranges
// - Huwawei Cloud, does not publish is ranges
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

type OracleCloudData = {
	last_updated_timestamp: string;
	regions: {
		region: string;
		cidrs: {
			cidr: string;
			tags: string[];
		}[];
	}[];
};

type VultrData = {
	asn: number;
	email: string;
	updated: string;
	subnets: {
		ip_prefix: string;
		alpha2code: string;
		region: string;
		city: string;
		postal_code: string;
	}[];
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
		tags: string[];
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
		for (const prefix of data.result.ipv4_cidrs) {
			result.push({
				csp: 'cloudflare',
				ipPrefix: prefix,
				meta: { service: 'CLOUDFLARE' },
			});
		}
		for (const prefix of data.result.ipv6_cidrs) {
			result.push({
				csp: 'cloudflare',
				ipPrefix: prefix,
				meta: { service: 'CLOUDFLARE' },
			});
		}
		for (const prefix of data.result.jdcloud_cidrs) {
			result.push({
				csp: 'cloudflare',
				ipPrefix: prefix,
				meta: { service: 'JD_CLOUD' },
			});
		}

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
		for (const rowRaw of data.split('\n')) {
			const [ipPrefix, countryCode, subdivisionCode, city, postalCode] = rowRaw.split(',');
			result.push({
				csp: 'digital_ocean',
				ipPrefix: ipPrefix,
				meta: { countryCode, subdivisionCode, city, postalCode },
			});
		}

		return result;
	}

	if (provider === 'IBM') {
		// IBM does not provide simple machine-readable format, so we scrape it from their documentation
		// https://cloud.ibm.com/docs/security-groups?topic=security-groups-ibm-cloud-ip-ranges
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: 'https://raw.githubusercontent.com/ibm-cloud-docs/infrastructure-hub/refs/heads/master/ips.md',
		})) as string;

		// Parse IP prefixes from all the Markdown tables
		const result: PrefixData[] = [];
		for (const line of data.split('\n')) {
			// Check if this is a table data row (starts with |)
			if (line.trim().startsWith('|')) {
				for (const match of line.matchAll(CIDR_REGEX)) {
					result.push({
						csp: 'IBM',
						ipPrefix: match[1],
						meta: {},
					});
				}
			}
		}

		return result;
	}

	if (provider === 'oracle_cloud') {
		// https://docs.oracle.com/en-us/iaas/Content/General/Concepts/addressranges.htm
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: 'https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json',
		})) as OracleCloudData;

		const result: PrefixData[] = [];
		for (const region of data.regions) {
			for (const cidr of region.cidrs) {
				result.push({
					csp: 'oracle_cloud',
					ipPrefix: cidr.cidr,
					meta: { region: region.region, tags: cidr.tags },
				});
			}
		}
		return result;
	}

	if (provider === 'vultr') {
		// https://docs.vultr.com/vultr-ip-space
		const data = (await functions.helpers.httpRequest({
			method: 'GET',
			url: 'https://geofeed.constant.com/?json',
		})) as VultrData;

		const result: PrefixData[] = [];
		for (const subnet of data.subnets) {
			result.push({
				csp: 'vultr',
				ipPrefix: subnet.ip_prefix,
				meta: {
					region: subnet.region,
					countryCode: subnet.alpha2code,
					city: subnet.city,
					postalCode: subnet.postal_code,
				},
			});
		}
		return result;
	}

	provider satisfies never;

	return null;
}
