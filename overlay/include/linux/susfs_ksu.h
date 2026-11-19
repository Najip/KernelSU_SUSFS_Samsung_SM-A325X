/* SPDX-License-Identifier: GPL-2.0 */
#ifndef _LINUX_SUSFS_KSU_H
#define _LINUX_SUSFS_KSU_H

#include <linux/types.h>

struct cred;
struct file;
struct page;

/* Native KernelSU APIs. */
#ifdef CONFIG_KSU
int ksu_handle_sys_read(unsigned int fd, char __user **buf, size_t *count);
#endif

#ifdef CONFIG_KSU_SUSFS
#define SUSFS_KSU_INSTALL_MAGIC1 0xDEADBEEF
extern struct cred *ksu_cred;
bool susfs_is_current_ksu_domain(void);
int ksu_handle_sys_reboot(int magic1, int magic2, unsigned int cmd,
			  void __user **arg);
/* Parent-kernel glue (fs/susfs_ksu_glue.c): SUSFS commands, then KernelSU. */
int susfs_ksu_sys_reboot(int magic1, int magic2, unsigned int cmd,
			 void __user **arg);

/* Optional SELinux-hide hooks (weak no-op fallbacks in fs/susfs_ksu_glue.c). */
extern bool ksu_selinux_hide_running;
extern struct page *fake_status;
void initialize_fake_status(void);
ssize_t my_write_context(struct file *file, char *buf, size_t size);
ssize_t my_write_access(struct file *file, char *buf, size_t size);
int my_setprocattr(const char *name, void *value, size_t size);
#endif
#endif
