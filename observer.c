/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer.c
 * ---------------------------
 * Observer. It executes a command from stdin, and captures the command's
 * stdout and stderr output, and send data to recorder.
 * NOTE it heavily relies on POSIX - incompatible with Windows.
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
    
    int attempt = 0;
    while (attempt < kClientMaxAttempts) {
        size_t sendLen = len < kPacketMaxLen ? len : kPacketMaxLen;
        int status = sendData(data, sendLen, ++attempt);
        /* the current design decision is that the observer would not wait for the server
         * to ACK, and the server would not ACK. Much like a UDP. */
        if (status == kClientSendDataSuccess) { break; }
        else { /* errors */
            /* server might be overwhelmed; we wait for a while before retrying */
            usleep(5e4); /* 5e4 micro second: 50 millisecond */
        }
    }

    freeOutputs(&outputs);
    free(data);
    return 0;
}

void captureOutputs(outputs_t *outputs, int stdoutRead, int stderrRead) {
    outputs->stdoutSize = read(stdoutRead, outputs->stdoutStr, kMaxRead);
    outputs->stderrSize = read(stderrRead, outputs->stderrStr, kMaxRead);
    return;
}

int sendData(char *data, size_t len, int attempt) {
    int clientSocketOrErrorStatus = createClientSocket(kRecorderHost, kRecorderPort, attempt);
    if (clientSocketOrErrorStatus < 0) {
        fprintf(stderr, "[Error] observer: abort\n");
        return clientSocketOrErrorStatus;
    }
    int clientSocket = clientSocketOrErrorStatus;
    int status = writeString(clientSocket, data, len);
    if (status == kClientWriteSocketError) {
        return kClientWriteSocketError;
    }
    closeClientSocket(clientSocket);
    return kClientSendDataSuccess;
}

/* system call send() does the same work if the flag parameter is zero */
int writeString(int fd, const char *str, size_t len) {
    size_t nBytesWritten = 0;
    while (nBytesWritten < len) {
        /* normally this loop only has one iteration */
        ssize_t ret = write(fd, str + nBytesWritten, len - nBytesWritten);
        if (ret < 0) {
            return kClientWriteSocketError;
        }
        nBytesWritten += ret;
    }
    return kClientSendDataSuccess;
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
