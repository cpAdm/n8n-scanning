import {readFile} from 'fs/promises';
import * as path from 'path';
import * as assert from "node:assert";
import {N8N_API} from "./utils/n8n";
import * as dotenv from 'dotenv';

dotenv.config(); // load .env file into process.env
const {N8N_URL, N8N_API_KEY} = process.env;
const WORKFLOW_FILE = path.join(__dirname, 'workflows', 'Nmap.json');

async function runWithTimeout<T>(
    task: () => Promise<T>,
    cleanup: () => void,
    delay: number
): Promise<T> {
    let timer: NodeJS.Timeout;
    const timeout = new Promise<never>((_, reject) => {
        timer = setTimeout(
            () => reject(new Error(`Timed out after ${delay / 1_000} seconds`)),
            delay,
        );
    });
    try {
        return await Promise.race([task(), timeout]);
    } finally {
        clearTimeout(timer);
        cleanup();
    }
}


async function main() {
    const api = new N8N_API(N8N_URL, N8N_API_KEY);

    const workflowData = JSON.parse(await readFile(WORKFLOW_FILE, 'utf-8'));
    const uploadedWorkflow = await api.createWorkflow(workflowData)
    const publishedWorkflow = await api.publishWorkflow(uploadedWorkflow)

    async function triggerWebhook() {
        const webhookNode = publishedWorkflow.nodes.find(node => node.webhookId)
        const webhookResponse = await fetch(`${N8N_URL}/webhook/${webhookNode.webhookId}`, {
            method: 'GET',
        });
        const [result] = await webhookResponse.json();
        assert.ok(webhookResponse.ok, result)

        console.log('Webhook triggered:', JSON.stringify(result, null, 2));
        assert.match(
            result.command,
            /^nmap -p 80 -oX \/tmp\/[a-f0-9]+xml -iL \/tmp\/[a-f0-9]+txt --excludefile \/tmp\/[a-f0-9]+txt$/
        )
        assert.match(
            result.stdout,
            /^Starting Nmap 7\.97 \( https:\/\/nmap\.org \) at \d{4}-\d{2}-\d{2} \d{2}:\d{2} \+0000\nNmap scan report for scanme\.nmap\.org \(45\.33\.32\.156\)\nHost is up \([0-9.]+s latency\)\.\nOther addresses for scanme\.nmap\.org \(not scanned\): [0-9a-f:]+\n\nPORT\s+STATE\s+SERVICE\n80\/tcp\s+open\s+http\n\nNmap done: 1 IP address \(1 host up\) scanned in [0-9.]+ seconds$/
        )
    }

    // Kill test after 30s, to avoid accidental DOS
    await runWithTimeout(triggerWebhook, async () => {
        const [execution] = await api.getExecutions(publishedWorkflow);
        await api.deleteExecution(execution);
        await api.deleteWorkflow(publishedWorkflow)
    }, 30_000)
}


// TODO transform file to nodejs testing lib https://nodejs.org/api/test.html
main();
