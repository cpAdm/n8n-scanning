import { spawn } from 'node:child_process';
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
 * Spawn command and stream outputs to avoid exec() maxBuffer limits.
 */
export async function execPromise(command: string): Promise<IExecReturnData> {
	const returnData = emptyReturnData();

	return await new Promise((resolve) => {
		const childProcess = spawn(command, {
			cwd: SHARED_DIR,
			shell: true,
		});

		childProcess.stdout.on('data', (chunk) => {
			returnData.stdout += chunk.toString();
		});

		childProcess.stderr.on('data', (chunk) => {
			returnData.stderr += chunk.toString();
		});

		childProcess.on('error', (error) => {
			returnData.error = error;
		});

		childProcess.on('close', (code, signal) => {
			returnData.exitCode = code ?? 1;
			if (signal) {
				returnData.stderr += `\nProcess terminated by signal ${signal}`;
			}

			returnData.stdout = returnData.stdout.trim();
			returnData.stderr = returnData.stderr.trim();
			resolve(returnData);
		});
	});
}
