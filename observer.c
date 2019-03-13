/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer.c
 * ---------------------------
 * Observer. It executes a command in Makefile, and captures the command's
 * stdout and stderr output.
 */

#include "observer.h"

int runCommand(char *cmd[]) {
    /* setting up two pipes */
    int stdoutPipe[2];
    int stderrPipe[2];
    if (pipe(stdoutPipe) || pipe(stderrPipe)) {
        fprintf(stderr, "[Error] pipe()\n");
    }
    
    time_report_t times;
    recordTime(&times, kStart);

	subprocess_t sp = { fork(), stdoutPipe[kRead], stderrPipe[kRead] }; 
	
    if (sp.pid == 0) { /* child process */
        /* prevent child from reading from pipe */
        close(stdoutPipe[kRead]);
        close(stderrPipe[kRead]);

        /* redirect the child's stdout, stderr FD to the pipe's writing end */
        dup2(stdoutPipe[kWrite], STDOUT_FILENO);
        dup2(stderrPipe[kWrite], STDERR_FILENO);
        close(stdoutPipe[kWrite]);
        close(stderrPipe[kWrite]);

        /* execute the command */
        execvp(cmd[0], cmd);
        /* if the child process reaches here, the execvp() encounters an error */
        fprintf(stderr, "[Error] execvp : %s\n", *cmd);
        return 1;
	}
	
    /* parent process */
    
    /* prevent parent from writing to pipe */
    close(stdoutPipe[kWrite]);
    close(stderrPipe[kWrite]);
    
    int status;
    waitpid(sp.pid, &status, 0);

    recordTime(&times, kFinish);

    if (WIFEXITED(status)) {
        outputs_t outputs;
        if (callocOutputs(&outputs)) {
            freeOutputs(&outputs);
            return 1;
        }

        /* capture output and handle it */
        captureOutputs(&outputs, sp.stdoutRead, sp.stderrRead);
        calcElapsed(&times);
        forwardOutputs(&outputs, &times);

        freeOutputs(&outputs);

        /* use the child's exit status: WIFEXITED() returns true if program
         * exits without being interrupted by signal */
        return WEXITSTATUS(status);
    }
    else {
        printSignal(stderr, WTERMSIG(status));
        return 1;
    }
}

void captureOutputs(outputs_t *outputs, int stdoutRead, int stderrRead) {
    outputs->stdoutSize = read(stdoutRead, outputs->stdoutStr, kMaxRead);
    outputs->stderrSize = read(stderrRead, outputs->stderrStr, kMaxRead);
    return;
}

void forwardOutputs(outputs_t *const outputs, time_report_t *const times) {
    fprintf(stdout, "(stdout) %s\n", outputs->stdoutSize ? outputs->stdoutStr : "(empty)");
    fprintf(stderr, "(stderr) %s\n", outputs->stderrSize ? outputs->stderrStr : "(empty)");
    fprintf(stdout, "time %f %f\n",
            (times->proc[kElapsed].tv_sec + times->proc[kElapsed].tv_nsec / 1e9),
            (times->real[kElapsed].tv_sec + times->real[kElapsed].tv_nsec / 1e9));
}

static void sigHandler(int sig) {
    printSignal(stderr, sig);
    exit(1); /* Exit the process, otherwise it keeps running into
                the same signal each time the process resumes */
}

int main(int argc, char *argv[]) {
    signal(SIGINT, sigHandler);
    signal(SIGABRT, sigHandler);
    signal(SIGSEGV, sigHandler);
	if (argc == 1) {
		fprintf(stderr, "[Error] no command\n");
		return 1;
	}
	return runCommand(argv + 1);
}
