import {readFile} from 'fs/promises';
import * as path from 'path';
import * as assert from "node:assert";
import {test} from "node:test";
import {N8N_API} from "./utils/n8n";
import * as dotenv from 'dotenv';

dotenv.config(); // load .env file into process.env
const {N8N_URL, N8N_API_KEY} = process.env;
const WORKFLOW_FILE = path.join(__dirname, 'workflows', 'Nmap.json');

test(
    'N8N workflow webhook triggers correctly',
    {timeout: 30_000}, // Kill test after 30s, to avoid accidental DOS
    async (t) => {
        const api = new N8N_API(N8N_URL, N8N_API_KEY);

        const workflowData = JSON.parse(await readFile(WORKFLOW_FILE, 'utf-8'));
        const uploadedWorkflow = await api.createWorkflow(workflowData);
        const publishedWorkflow = await api.publishWorkflow(uploadedWorkflow);

        t.after(async () => {
            const [execution] = await api.getExecutions(publishedWorkflow);
            if (execution) await api.deleteExecution(execution);
            await api.deleteWorkflow(publishedWorkflow);
        });

        const webhookNode = publishedWorkflow.nodes.find(node => node.webhookId);
        const webhookResponse = await fetch(`${N8N_URL}/webhook/${webhookNode.webhookId}`, {
            method: 'GET',
        });
        const [result] = await webhookResponse.json();
        assert.ok(webhookResponse.ok, JSON.stringify(result, null, 2));

        console.log('Webhook triggered:', JSON.stringify(result, null, 2));
        assert.match(
            result.command,
            /^nmap -p 80 -oX \/tmp\/[a-f0-9]+xml -iL \/tmp\/[a-f0-9]+txt --excludefile \/tmp\/[a-f0-9]+txt$/
        );
        assert.match(
            result.stdout,
            /^Starting Nmap 7\.97 \( https:\/\/nmap\.org \) at .*?\nNmap scan report for scanme\.nmap\.org \(45\.33\.32\.156\)\nHost is up \([0-9.]+s latency\)\.\nOther addresses for scanme\.nmap\.org \(not scanned\): .*?\n\nPORT\s+STATE\s+SERVICE\n80\/tcp\s+open\s+http\n\nNmap done: 1 IP address \(1 host up\) scanned in [0-9.]+ seconds$/
        );
    }
);