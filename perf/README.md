# perf

This provides a very rudimentary performance analysis. Very basic, really.

Make command:
```shell
make -f N.make
```

Craft command:
```shell
../craft.py -- -f N.make
```

In this directory:

```shell
$ ./perf.py 2 # run 2 makefiles
run: 0.make     observed commands: 0
run: 1.make     observed commands: 1
filename   |  make      craft   overhead
-----------|---------------------------
0.make     |   0.011,   0.156,  1350.80 %
1.make     |   1.018,   1.166,  14.47 %
```

```shell
$ ./perf.py # run all makefiles
run: 0.make     observed commands: 0
run: 1.make     observed commands: 1
run: 2.make     observed commands: 2
run: 5.make     observed commands: 5
run: 10.make    observed commands: 10
run: 20.make    observed commands: 20
run: 50.make    observed commands: 50
run: 100.make   observed commands: 100
run: 200.make   observed commands: 200
filename   |  make      craft   overhead
-----------|-----------------------------
0.make     |  00.011,  00.154,  1324.01 %
1.make     |  01.020,  01.164,  14.16 %
2.make     |  02.032,  02.184,  7.44 %
5.make     |  05.062,  05.224,  3.19 %
10.make    |  10.117,  10.309,  1.90 %
20.make    |  20.211,  20.456,  1.21 %
50.make    |  50.520,  50.928,  0.81 %
100.make   |  101.049,  101.665,  0.61 %
200.make   |  202.112,  203.140,  0.51 %
```

![perf-all.png](perf-all.png)

```
overhead = python interpreter starting time
           + craft starting time
           + recorder server starting time
           + recorder log dumping disk I/O
           + N * (observer overhead + recorder handling overhead)
         ~ C + N * a
         ~ O(N)

	fixed overhead    C = 0.1504 sec
	variable overhead a = 0.0045 sec / command
```

Platform for the results above: macOS 10.14, Python 2.7, Clang -O3, 2.5 GHz Intel Core i7

###### EOF