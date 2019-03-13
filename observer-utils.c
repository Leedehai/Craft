/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer-utils.c
 * ---------------------------
 * Observer utilities.
 */

#include "observer.h"

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

static void subtractTime(ntime_t * const t1, ntime_t * const t2, ntime_t *dt) {
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
