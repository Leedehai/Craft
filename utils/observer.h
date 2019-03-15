/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer.h
 * ---------------------------
 * Observer. It executes a command from stdin, and captures the command's
 * stdout and stderr output, and send data to recorder.
 * NOTE it heavily relies on POSIX - incompatible with Windows.
 */

#ifndef OBSERVER_H_
#define OBSERVER_H_

/* to work with GCC, these macros should be defined (one is sufficient, but I defined
 * both just in case); Clang doesn't need them */
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 19940123L

#include <memory.h>
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

static const int kClientSocketError = -1;
static const int kDefaultBacklog = 128;

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

/* stdout, stderr, times, command, exit code */
static const size_t kPacketMaxLen = 4096 * 2 + 256 + 1024 + 8 + 100;

int report(subprocess_t *, time_report_t *, char *cmd[], int exitCode);
void captureOutputs(outputs_t *, int stdoutRead, int stderrRead);
void sendData(char *data, size_t len);
void writeString(int fd, const char *str, size_t len);

size_t serializeData(
    char *data, outputs_t *, time_report_t *, char *cmd[], int exitCode);

int createClientSocket(const char *host, unsigned short port);
void closeClientSocket(int sock);

int callocOutputs(outputs_t *);
void freeOutputs(outputs_t *);

void recordTime(time_report_t *times, int which);
double ntimeToSec(ntime_t *t);
void calcElapsed(time_report_t *times);

const char *getSignalName(int sig);
void printSignal(FILE *f, int sig);

#endif
