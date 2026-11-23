#!/system/bin/sh
# A32 JPEG + BBR fix. The fix is by Juan (LumiROM): his odm patch
# "odm-9.0.0-JPEG-BBR-PARCHE_A325F" does the same in /odm/etc/init/local_a32.rc.
#
# 1) Blank JPEG photos: the vendor turns on ro.vendor.jpeg_decode_sw_opt=1, and
#    One UI 9's libhwui then asks for memory from the dma-buf heap "mtk_mm",
#    which this 4.14 kernel does not have. This switch turns that path off.
#    Runs before zygote, so every app starts with it.
setprop debug.jpegfull.opt.switch 0
# 2) BBR: the kernel default. The vendor's networksetting.rc sets bic later,
#    so service.sh sets BBR again.
grep -qw bbr /proc/sys/net/ipv4/tcp_available_congestion_control 2>/dev/null \
  && echo bbr > /proc/sys/net/ipv4/tcp_congestion_control
