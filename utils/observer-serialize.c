/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer-serialize.c
 * ---------------------------
 * Observer's data serialization.
 */

#include "observer.h"

static void
appendString(char *dest, const char *src, size_t count, size_t *pos) {
    memcpy(dest + *pos, src, count);
    *pos += count;
}

static void
appendDouble(char *dest, const char *fmt, double value, size_t *pos) {
    int count = sprintf(dest + *pos, fmt, value);
    *pos += count;
}

/* Like Protobuf, albeit very simple and rudimentary */
size_t serializeData(char *data,
                     outputs_t *const outputs,
                     time_report_t *const times,
                     char *cmd[],
                     int exitCode) {
    static const char *kExitCodeHeader    = "[#exit#]";
    static const int   kExitCodeHeaderLen = 8; /* not counting '\0' */
    static const char *kCommandHeader    = "[#cmd#]";
    static const int   kCommandHeaderLen = 7; /* not counting '\0' */
    static const char *kStdoutHeader    = "[#out#]";
    static const int   kStdoutHeaderLen = 7; /* not counting '\0' */
    static const char *kStderrHeader    = "[#err#]";
    static const int   kStderrHeaderLen = 7; /* not counting '\0' */
    static const char *kTimesHeader    = "[#time#]";
    static const int   kTimesHeaderLen = 8; /* not counting '\0' */
    
    size_t pos = 0;

    appendString(data, kExitCodeHeader, kExitCodeHeaderLen, &pos);
    appendString(data, exitCode ? "1" : "0", 1, &pos);

    appendString(data, kCommandHeader, kCommandHeaderLen, &pos);
    char **part = cmd;
    while (*part) {
        appendString(data, *part, strlen(*part), &pos);
        appendString(data, " ", 1, &pos);
        ++part;
    }

    appendString(data, kStdoutHeader, kStdoutHeaderLen, &pos);
    appendString(data, outputs->stdoutStr, outputs->stdoutSize, &pos);

    appendString(data, kStderrHeader, kStderrHeaderLen, &pos);
    appendString(data, outputs->stderrStr, outputs->stderrSize, &pos);

    appendString(data, kTimesHeader, kTimesHeaderLen, &pos);
    appendDouble(data, "%f", ntimeToSec(&(times->proc[kStart])), &pos);
    appendString(data, ",", 1, &pos);
    appendDouble(data, "%f", ntimeToSec(&(times->proc[kFinish])), &pos);
    appendString(data, ",", 1, &pos);
    appendDouble(data, "%f", ntimeToSec(&(times->proc[kElapsed])), &pos);
    appendString(data, ";", 1, &pos);
    appendDouble(data, "%f", ntimeToSec(&(times->real[kStart])), &pos);
    appendString(data, ",", 1, &pos);
    appendDouble(data, "%f", ntimeToSec(&(times->real[kFinish])), &pos);
    appendString(data, ",", 1, &pos);
    appendDouble(data, "%f", ntimeToSec(&(times->real[kElapsed])), &pos);

    return pos;
}
