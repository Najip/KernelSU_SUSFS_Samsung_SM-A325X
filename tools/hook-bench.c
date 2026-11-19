// SPDX-License-Identifier: GPL-2.0
/*
 * hook-bench: times the syscalls that xxKSU hooks, so the three hook
 * styles (manual, syscall_table, branch_link) can be compared on the phone.
 *
 * Built without any C library (raw arm64 syscalls), so the same binary runs
 * from Termux, adb shell or TWRP. Usage:
 *   hook-bench [loops]          default 200000 (execve test uses loops/400)
 *
 * Each test runs 7 rounds and prints the median and the best round in
 * nanoseconds per call. Lower is better. Run it a few times; the phone's
 * clock speed changes with temperature and load.
 */
typedef unsigned long u64;
typedef long s64;

#define AT_FDCWD -100
#define SIGCHLD 17
#define CLOCK_MONOTONIC 1

#define __NR_faccessat 48
#define __NR_openat 56
#define __NR_close 57
#define __NR_read 63
#define __NR_write 64
#define __NR_newfstatat 79
#define __NR_fstat 80
#define __NR_exit 93
#define __NR_clock_gettime 113
#define __NR_getuid 174
#define __NR_clone 220
#define __NR_execve 221
#define __NR_wait4 260

static inline s64 sc6(s64 n, s64 a, s64 b, s64 c, s64 d, s64 e, s64 f)
{
	register s64 x8 __asm__("x8") = n;
	register s64 x0 __asm__("x0") = a;
	register s64 x1 __asm__("x1") = b;
	register s64 x2 __asm__("x2") = c;
	register s64 x3 __asm__("x3") = d;
	register s64 x4 __asm__("x4") = e;
	register s64 x5 __asm__("x5") = f;
	__asm__ volatile("svc #0"
			 : "+r"(x0)
			 : "r"(x8), "r"(x1), "r"(x2), "r"(x3), "r"(x4), "r"(x5)
			 : "memory", "cc");
	return x0;
}
#define sc(n, a, b, c, d) sc6(n, (s64)(a), (s64)(b), (s64)(c), (s64)(d), 0, 0)

struct timespec { s64 sec; s64 nsec; };
static char statbuf[256] __attribute__((aligned(16)));

static u64 now_ns(void)
{
	struct timespec t;
	sc(__NR_clock_gettime, CLOCK_MONOTONIC, &t, 0, 0);
	return (u64)t.sec * 1000000000ul + (u64)t.nsec;
}

static u64 slen(const char *s) { u64 n = 0; while (s[n]) n++; return n; }
static void out(const char *s) { sc(__NR_write, 1, s, slen(s), 0); }
static void outn(u64 v)
{
	char b[24]; int i = 23; b[i] = 0;
	do { b[--i] = '0' + v % 10; v /= 10; } while (v && i);
	out(&b[i]);
}
/* nanoseconds with one decimal: value is in tenths of a ns */
static void outt(u64 tenths) { outn(tenths / 10); out("."); outn(tenths % 10); }

static u64 atou(const char *s) { u64 v = 0; while (*s >= '0' && *s <= '9') v = v * 10 + (*s++ - '0'); return v; }

static const char *const su_path = "/system/bin/su";
static const char *const sh_path = "/system/bin/sh";
static const char *const true_path = "/system/bin/true";
static char *const true_argv[] = { (char *)"true", 0 };
static char *const empty_envp[] = { 0 };

enum { T_ACCESS_SU, T_ACCESS_SH, T_STAT_SU, T_STAT_SH, T_FSTAT, T_READ, T_EXEC };

static int zero_fd = -1;

static void run_once(int t, u64 n)
{
	u64 i;
	switch (t) {
	case T_ACCESS_SU: for (i = 0; i < n; i++) sc(__NR_faccessat, AT_FDCWD, su_path, 0, 0); break;
	case T_ACCESS_SH: for (i = 0; i < n; i++) sc(__NR_faccessat, AT_FDCWD, sh_path, 0, 0); break;
	case T_STAT_SU: for (i = 0; i < n; i++) sc(__NR_newfstatat, AT_FDCWD, su_path, statbuf, 0); break;
	case T_STAT_SH: for (i = 0; i < n; i++) sc(__NR_newfstatat, AT_FDCWD, sh_path, statbuf, 0); break;
	case T_FSTAT: for (i = 0; i < n; i++) sc(__NR_fstat, zero_fd, statbuf, 0, 0); break;
	case T_READ: for (i = 0; i < n; i++) sc(__NR_read, zero_fd, statbuf, 1, 0); break;
	case T_EXEC:
		for (i = 0; i < n; i++) {
			s64 pid = sc(__NR_clone, SIGCHLD, 0, 0, 0);
			if (pid == 0) {
				sc(__NR_execve, true_path, true_argv, empty_envp, 0);
				sc(__NR_exit, 127, 0, 0, 0);
			}
			if (pid > 0) {
				int st;
				sc(__NR_wait4, pid, &st, 0, 0);
			}
		}
		break;
	}
}

#define ROUNDS 7
static void bench(const char *name, int t, u64 n)
{
	u64 r[ROUNDS];
	int i, j;
	run_once(t, n / 10 + 1); /* warm up */
	for (i = 0; i < ROUNDS; i++) {
		u64 a = now_ns();
		run_once(t, n);
		r[i] = (now_ns() - a) * 10 / n; /* tenths of ns per call */
	}
	for (i = 1; i < ROUNDS; i++)
		for (j = i; j > 0 && r[j - 1] > r[j]; j--) { u64 x = r[j]; r[j] = r[j - 1]; r[j - 1] = x; }
	out(name);
	for (i = slen(name); i < 34; i++) out(" ");
	out("median "); outt(r[ROUNDS / 2]); out(" ns   best "); outt(r[0]); out(" ns\n");
}

static int main_c(int argc, char **argv)
{
	u64 n = 200000;
	if (argc > 1) { n = atou(argv[1]); if (n < 1000) n = 1000; }
	zero_fd = (int)sc(__NR_openat, AT_FDCWD, "/dev/zero", 0, 0);

	out("hook-bench: "); outn(n); out(" calls per round, uid "); outn((u64)sc(__NR_getuid, 0, 0, 0, 0)); out("\n");
	bench("faccessat /system/bin/su", T_ACCESS_SU, n);
	bench("faccessat /system/bin/sh", T_ACCESS_SH, n);
	bench("newfstatat /system/bin/su", T_STAT_SU, n);
	bench("newfstatat /system/bin/sh", T_STAT_SH, n);
	if (zero_fd >= 0) {
		bench("fstat (fd)", T_FSTAT, n);
		bench("read 1 byte", T_READ, n);
	}
	bench("fork + execve /system/bin/true", T_EXEC, n / 400 + 50);
	return 0;
}

/* entry point: sp -> argc, argv[] */
__attribute__((used)) void c_start(u64 *sp)
{
	int argc = (int)sp[0];
	char **argv = (char **)(sp + 1);
	sc(__NR_exit, main_c(argc, argv), 0, 0, 0);
	for (;;) { }
}
__asm__(".text\n.global _start\n_start:\n\tmov x0, sp\n\tand sp, x0, #~15\n\tbl c_start\n");
