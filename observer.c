/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer.c
 * ---------------------------
 * Observer. It executes a command in Makefile, and captures the command's
 * stdout and stderr output.
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

/* C disallows variable-sized array from initialization, hence I have
 * to define kMaxRead as a macro instead of a 'static const int' */
#define kMaxRead 4096

static const int kRead = 0;
static const int kWrite = 1;

typedef struct {
    int pid;        /* the subprocess's pid */
    int stdoutRead; /* read stdout from subprocess */
    int stderrRead; /* read stderr from subprocess */
} subprocess_t;

typedef struct {
    char *stdoutStr;
    char *stderrStr;
    ssize_t stdoutSize;
    ssize_t stderrSize;
} outputs_t;

void captureOutputs(outputs_t *, int stdoutRead, int stderrRead);
const char *getSignalName(int sig);
void printSignal(FILE *f, int sig);

int runCommand(char *cmd[]) {
    /* setting up two pipes */
    int stdoutPipe[2];
    int stderrPipe[2];
    if (pipe(stdoutPipe) || pipe(stderrPipe)) {
        fprintf(stderr, "[Error] pipe()\n");
    }
    /* fork */
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
    if (WIFEXITED(status)) {
        outputs_t outputs;

        /* capture output and handle it */
        captureOutputs(&outputs, sp.stdoutRead, sp.stderrRead);
        fprintf(stdout, "(stdout) %s\n", outputs.stdoutSize ? outputs.stdoutStr : "(empty)");
        fprintf(stderr, "(stderr) %s\n", outputs.stderrSize ? outputs.stderrStr : "(empty)");

        if (outputs.stdoutStr) { free(outputs.stdoutStr); }
        if (outputs.stderrStr) { free(outputs.stderrStr); }

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
    outputs->stdoutStr = (char *)calloc(kMaxRead, sizeof(char));
    outputs->stderrStr = (char *)calloc(kMaxRead, sizeof(char));
    if (!outputs->stdoutStr || !outputs->stderrStr) {
        fprintf(stderr, "[Error] error in calloc()\n");
        /* setting to 0 is necessary */
        outputs->stdoutSize = 0;
        outputs->stderrSize = 0;
        return;
    }
    outputs->stdoutSize = read(stdoutRead, outputs->stdoutStr, kMaxRead);
    outputs->stderrSize = read(stderrRead, outputs->stderrStr, kMaxRead);
    return;
}

static void sigHandler(int sig) {
    printSignal(stderr, sig);
    exit(1); /* Exit the process, otherwise it keeps running into
                the same signal each time the process resumes */
}

const char *getSignalName(int sig) {
    switch (sig) {
    case 2:  return "SIGINT (2)";
    case 6:  return "SIGABRT (6)";
    case 11: return "SIGSEGV (11)";
    default: return 0;
    }
}

void printSignal(FILE *f, int sig) {
    const char *sigName = getSignalName(sig);
    if (sigName) {
        fprintf(f, "[Signal] child interrupted by signal %s\n", sigName);
    }
    else {
        fprintf(f, "[Signal] child interrupted by signal %d\n", sig);
    }
    return;
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
