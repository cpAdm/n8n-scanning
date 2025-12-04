import { exec } from 'node:child_process';
import os from 'node:os';

interface IExecReturnData {
	exitCode: number;
	error?: Error;
	stderr: string;
	stdout: string;
}

export function emptyReturnData(): IExecReturnData {
	return {
		error: undefined,
		exitCode: 0,
		stderr: '',
		stdout: '',
	};
}

/**
 * Promisifiy exec manually to also get the exit code
 * (copied from n8n's ExecuteCommand.node.ts)
 */
export async function execPromiseInTmp(command: string): Promise<IExecReturnData> {
	const returnData = emptyReturnData();
	// We cannot use process.cwd() as current user does not have write permissions there
	const cwd = os.tmpdir();

	return await new Promise((resolve) => {
		// TODO can we stream progress via this.sendMessageToUI (F12 console) for debugging?
		exec(command, { cwd: cwd }, (error, stdout, stderr) => {
			returnData.stdout = stdout.trim();
			returnData.stderr = stderr.trim();

			if (error) {
				returnData.error = error;
			}

			resolve(returnData);
		}).on('exit', (code) => {
			returnData.exitCode = code || 0;
		});
	});
}
