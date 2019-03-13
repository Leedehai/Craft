/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer.c
 * ---------------------------
 * Observer. It executes a command in Makefile, and captures the command's
 * stdout and stderr output.
 */

/* to work with GCC, these macros are necessary (one is sufficient, but I defined
 * both just in case); Clang doesn't need them */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 19940123L

#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

/* C disallows variable-sized array from initialization, hence I have
 * to define kMaxRead as a macro instead of a 'static const int' */
#define kMaxRead 4096

enum { kRead = 0, kWrite = 1 };

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

typedef struct timespec ntime_t;
typedef struct {
    ntime_t proc[3];
    ntime_t real[3];
} time_report_t;
enum { kStart = 0, kFinish = 1, kElapsed = 2 };

void captureOutputs(outputs_t *, int stdoutRead, int stderrRead);
void forwardOutputs(outputs_t *, time_report_t *);

int callocOutputs(outputs_t *);
void freeOutputs(outputs_t *);
void recordTime(time_report_t *times, int which);
void calcElapsed(time_report_t *times);
const char *getSignalName(int sig);
void printSignal(FILE *f, int sig);

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

/* utilities */

int callocOutputs(outputs_t *outputs) {
    outputs->stdoutStr = (char *)calloc(kMaxRead, sizeof(char));
    outputs->stderrStr = (char *)calloc(kMaxRead, sizeof(char));
    if (!outputs->stdoutStr || !outputs->stderrStr) {
        fprintf(stderr, "[Error] error in calloc()\n");
        return 1;
    }
    return 0;
}

void freeOutputs(outputs_t *outputs) {
    if (outputs->stdoutStr) { free(outputs->stdoutStr); }
    if (outputs->stderrStr) { free(outputs->stderrStr); }
}

void recordTime(time_report_t *times, int which) {
    clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &(times->proc[which]));
    clock_gettime(CLOCK_REALTIME, &(times->real[which]));
}

void subtractTime(ntime_t * const t1, ntime_t * const t2, ntime_t *dt) {
    dt->tv_nsec = t2->tv_nsec - t1->tv_nsec;
    dt->tv_sec  = t2->tv_sec - t1->tv_sec;
    if (dt->tv_sec > 0 && dt->tv_nsec < 0) {
        dt->tv_nsec += 1e9;
        dt->tv_sec -= 1;
    }
    else if (dt->tv_sec < 0 && dt->tv_nsec > 0) {
        dt->tv_nsec -= 1e9;
        dt->tv_sec += 1;
    }
}

void calcElapsed(time_report_t *times) {
    subtractTime(&(times->proc[kStart]), &(times->proc[kFinish]), &(times->proc[kElapsed]));
    subtractTime(&(times->real[kStart]), &(times->real[kFinish]), &(times->real[kElapsed]));
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
