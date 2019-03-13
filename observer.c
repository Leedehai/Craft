/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer.c
 * ---------------------------
 * Observer. It executes a command in Makefile, and captures the command's
 * stdout and stderr output.
 * NOTE it heavily relies on POSIX libraries.
 */

#include "observer.h"
#include <string.h>

/* the server ports */
static const char *kRecorderHost = "localhost";
static const int kRecorderPort = 8081;

int runCommand(char *cmd[]) {
    /* setting up two pipes */
    int stdoutPipe[2];
    int stderrPipe[2];
    if (pipe(stdoutPipe) || pipe(stderrPipe)) {
        fprintf(stderr, "[Error] observer: pipe not established\n");
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
        fprintf(stderr, "[Error] observer: execvp : %s\n", *cmd);
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
        int exitCode = WEXITSTATUS(status);
        return report(&sp, &times, cmd, exitCode);
    }
    else {
        printSignal(stderr, WTERMSIG(status));
        return 1;
    }
}

int report(subprocess_t *sp, time_report_t *times, char *cmd[], int exitCode) {
    outputs_t outputs;
    if (callocOutputs(&outputs)) {
        freeOutputs(&outputs);
        return 1;
    }

    /* capture output and handle it */
    captureOutputs(&outputs, sp->stdoutRead, sp->stderrRead);
    calcElapsed(times);

    char *data = (char *)calloc(kPacketMaxLen, sizeof(char *));
    if (!data) {
        fprintf(stderr, "[Error] observer: error in calloc()\n");
        return 1;
    }
    size_t len = serializeData(data, &outputs, times, cmd, exitCode);
    sendData(data, len < kPacketMaxLen ? len : kPacketMaxLen);

    freeOutputs(&outputs);
    free(data);
    return 0;
}

void captureOutputs(outputs_t *outputs, int stdoutRead, int stderrRead) {
    outputs->stdoutSize = read(stdoutRead, outputs->stdoutStr, kMaxRead);
    outputs->stderrSize = read(stderrRead, outputs->stderrStr, kMaxRead);
    return;
}

static void printString(char *dest, const char *src, size_t count, size_t *pos) {
    memcpy(dest + *pos, src, count);
    *pos += count;
}

static void printDouble(char *dest, const char *fmt, double value, size_t *pos) {
    int count = sprintf(dest + *pos, fmt, value);
    *pos += count;
}

/* Like Protobuf, albeit very simple and rudimentary */
size_t serializeData(char *data,
                     outputs_t *const outputs,
                     time_report_t *const times,
                     char *cmd[],
                     int exitCode) {
    static const char *kExitCodeHeader    = "[[exit]]";
    static const int   kExitCodeHeaderLen = 8; /* not counting '\0' */
    static const char *kCommandHeader    = "[[cmd]]";
    static const int   kCommandHeaderLen = 7; /* not counting '\0' */
    static const char *kStdoutHeader    = "[[out]]";
    static const int   kStdoutHeaderLen = 7; /* not counting '\0' */
    static const char *kStderrHeader    = "[[err]]";
    static const int   kStderrHeaderLen = 7; /* not counting '\0' */
    static const char *kTimesHeader    = "[[time]]";
    static const int   kTimesHeaderLen = 8; /* not counting '\0' */
    
    size_t pos = 0;

    printString(data, kExitCodeHeader, kExitCodeHeaderLen, &pos);
    printString(data, exitCode ? "1" : "0", 1, &pos);

    printString(data, kCommandHeader, kCommandHeaderLen, &pos);
    char **part = cmd;
    while (*part) {
        printString(data, *part, strlen(*part), &pos);
        printString(data, " ", 1, &pos);
        ++part;
    }

    printString(data, kStdoutHeader, kStdoutHeaderLen, &pos);
    printString(data, outputs->stdoutStr, outputs->stdoutSize, &pos);

    printString(data, kStderrHeader, kStderrHeaderLen, &pos);
    printString(data, outputs->stderrStr, outputs->stderrSize, &pos);

    printString(data, kTimesHeader, kTimesHeaderLen, &pos);
    printDouble(data, "%f", ntimeToSec(&(times->proc[kStart])), &pos);
    printString(data, ",", 1, &pos);
    printDouble(data, "%f", ntimeToSec(&(times->proc[kFinish])), &pos);
    printString(data, ",", 1, &pos);
    printDouble(data, "%f", ntimeToSec(&(times->proc[kElapsed])), &pos);
    printString(data, ";", 1, &pos);
    printDouble(data, "%f", ntimeToSec(&(times->real[kStart])), &pos);
    printString(data, ",", 1, &pos);
    printDouble(data, "%f", ntimeToSec(&(times->real[kFinish])), &pos);
    printString(data, ",", 1, &pos);
    printDouble(data, "%f", ntimeToSec(&(times->real[kElapsed])), &pos);

    return pos;
}

void sendData(char *data, size_t len) {
    int clientSocket = createClientSocket(kRecorderHost, kRecorderPort);
    if (clientSocket == kClientSocketError) {
        fprintf(stderr, "[Error] observer: abort\n");
        return;
    }
    writeString(clientSocket, data, len);
    closeClientSocket(clientSocket);
}

void writeString(int fd, const char *str, size_t len) {
    size_t nBytesWritten = 0;
    while (nBytesWritten < len) {
        /* normally this loop only has one iteration */
        nBytesWritten += write(fd, str + nBytesWritten, len - nBytesWritten);
    }
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
		fprintf(stderr, "[Error] observer: no command\n");
		return 1;
	}
	return runCommand(argv + 1);
}
