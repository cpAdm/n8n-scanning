import { exec } from 'node:child_process';
import { SHARED_DIR } from './file';

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
export async function execPromise(command: string): Promise<IExecReturnData> {
	const returnData = emptyReturnData();

	return await new Promise((resolve) => {
		// TODO can we stream progress via this.sendMessageToUI (F12 console) for debugging?
		exec(command, { cwd: SHARED_DIR }, (error, stdout, stderr) => {
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
