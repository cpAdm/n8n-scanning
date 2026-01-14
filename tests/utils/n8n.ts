import * as assert from "node:assert";

export type Execution = {
    id: string;
};

export type Workflow = {
    id: string;
    nodes: {
        webhookId: string
    }[]
};

// Not all fields from the exported workflow are expected by the API
// https://docs.n8n.io/api/api-reference/#tag/workflow/POST/workflows
function cleanWorkflowForAPI(workflow: Record<string, unknown>) {
    return {
        connections: workflow.connections,
        name: workflow.name,
        nodes: workflow.nodes,
        settings: workflow.settings ?? {},
        shared: workflow.shared,
        staticData: workflow.staticData
    };
}

export class N8N_API {
    private readonly baseUrl: string;
    private readonly apiKey: string;

    constructor(baseUrl: string, apiKey: string) {
        this.baseUrl = baseUrl.replace(/\/+$/, '');
        this.apiKey = apiKey;
    }

    private async request<T = unknown>(
        relativeUrl: string,
        init: RequestInit = {},
    ): Promise<T> {
        const response = await fetch(
            `${this.baseUrl}/api/v1${relativeUrl}`,
            {
                ...init,
                headers: {
                    'X-N8N-API-KEY': this.apiKey,
                    ...init.headers,
                },
            },
        );

        let body: unknown;
        const hasBody = response.headers
            .get('content-type')
            ?.includes('application/json');

        if (hasBody) {
            body = await response.json();
        }

        assert.ok(response.ok, JSON.stringify(body, null, 2));

        return body as T;
    }

    async getExecutions(workflow: Workflow): Promise<Execution[]> {
        const result = await this.request<{ data: Execution[] }>(
            `/executions?workflowId=${workflow.id}`,
            {method: 'GET'},
        );
        return result.data;
    }

    async deleteExecution(execution: Execution): Promise<void> {
        await this.request<void>(
            `/executions/${execution.id}`,
            {method: 'DELETE'},
        );
    }

    async deleteWorkflow(workflow: Workflow): Promise<void> {
        await this.request<void>(
            `/workflows/${workflow.id}`,
            {method: 'DELETE'},
        );
    }

    async createWorkflow(workflowData: Record<string, unknown>,): Promise<Workflow> {
        return this.request(
            '/workflows',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(cleanWorkflowForAPI(workflowData)),
            },
        );
    }

    async publishWorkflow(workflow: Workflow): Promise<Workflow> {
        return this.request(
            `/workflows/${workflow.id}/activate`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
            },
        );
    }
}
