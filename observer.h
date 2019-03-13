/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer.h
 * ---------------------------
 * Observer. It executes a command in Makefile, and captures the command's
 * stdout and stderr output.
 */

#ifndef OBSERVER_H_
#define OBSERVER_H_

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

#endif
