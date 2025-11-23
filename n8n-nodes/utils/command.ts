import { exec } from 'child_process';

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
export async function execPromise(cwd: string, command: string): Promise<IExecReturnData> {
	const returnData = emptyReturnData();

	return await new Promise((resolve) => {
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
