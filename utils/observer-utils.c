/**
 * Copyright: see README and LICENSE under the project root directory.
 * Author: Haihong Li
 * 
 * file: observer-utils.c
 * ---------------------------
 * Observer utilities.
 */

#include "observer.h"
#include <netdb.h>      /* for gethostbyname */
#include <sys/socket.h> /* for socket, connect, etc. */
#include <arpa/inet.h>  /* for htonl, htons, sockaddr_in, etc. */

int createClientSocket(const char *host, unsigned short port) {
  struct hostent *he = gethostbyname(host);
  if (he == NULL) {
      fprintf(stderr, "[Error] observer: host not resolved: %s\n", host);
      return kClientSocketError;
  }

  int sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock < 0) {
      fprintf(stderr, "[Error] observer: error when creating client socket\n");
      return kClientSocketError;
  }
  
  struct sockaddr_in serverAddress;
  memset(&serverAddress, 0, sizeof(serverAddress));
  serverAddress.sin_family = AF_INET;
  serverAddress.sin_port = htons(port);
  serverAddress.sin_addr.s_addr = 
    ((struct in_addr *)he->h_addr_list[0])->s_addr;
  
  if (connect(sock, (struct sockaddr *) &serverAddress, 
	      sizeof(serverAddress)) != 0) {
    fprintf(stderr, "[Error] observer: unable to connect %s:%d\n", host, port);
    close(sock);
    return kClientSocketError;
  }
  
  return sock;
}

void closeClientSocket(int sock) {
    close(sock);
}

int callocOutputs(outputs_t *outputs) {
    outputs->stdoutStr = (char *)calloc(kMaxRead, sizeof(char));
    outputs->stderrStr = (char *)calloc(kMaxRead, sizeof(char));
    if (!outputs->stdoutStr || !outputs->stderrStr) {
        fprintf(stderr, "[Error] observer: error in calloc()\n");
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

double ntimeToSec(ntime_t *t) {
    return t->tv_sec + t->tv_nsec / 1e9;
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
    subtractTime(
        &(times->proc[kStart]), &(times->proc[kFinish]),
        &(times->proc[kElapsed])
    );
    subtractTime(
        &(times->real[kStart]), &(times->real[kFinish]),
        &(times->real[kElapsed])
    );
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
