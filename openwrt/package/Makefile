include $(TOPDIR)/rules.mk

PKG_NAME:=wbd-next-v4
PKG_VERSION:=0.1.0
PKG_RELEASE:=1
PKG_LICENSE:=MIT
PKG_MAINTAINER:=WBD Next contributors

include $(INCLUDE_DIR)/package.mk

define Package/wbd-next-v4
  SECTION:=net
  CATEGORY:=Network
  TITLE:=WBD Next V4 experimental aarch64 client
  DEPENDS:=@TARGET_aarch64 +kmod-tun +ip-full +ca-bundle
endef

define Package/wbd-next-v4/description
  Experimental original-Go TLS / Rust V4 ARM64 client binaries.
  This package does not automatically install routes, a daemon, or credentials.
endef

# Supply an exact-SOURCE build artifact directory (no floating downloads).
# Both ELF files MUST be for the same aarch64-linux-musl runtime/API.
WBD_ARM64_STAGE ?=

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
endef

define Build/Compile
	test -n "$(WBD_ARM64_STAGE)"
	test -s "$(WBD_ARM64_STAGE)/wbd-v4-client"
	test -s "$(WBD_ARM64_STAGE)/libwbd_engine.so"
	test -s "$(WBD_ARM64_STAGE)/SHA256SUMS"
	(cd "$(WBD_ARM64_STAGE)" && sha256sum -c SHA256SUMS)
endef

define Package/wbd-next-v4/install
	$(INSTALL_DIR) $(1)/usr/bin $(1)/usr/lib $(1)/etc/init.d $(1)/etc/config
	$(INSTALL_BIN) $(WBD_ARM64_STAGE)/wbd-v4-client $(1)/usr/bin/wbd-v4-client
	$(INSTALL_DATA) $(WBD_ARM64_STAGE)/libwbd_engine.so $(1)/usr/lib/libwbd_engine.so\n\t$(INSTALL_BIN) ./files/wbd-next-v4.init $(1)/etc/init.d/wbd-next-v4\n\t$(INSTALL_CONF) ./files/wbd-next-v4.config $(1)/etc/config/wbd_next_v4
endef

$(eval $(call BuildPackage,wbd-next-v4))
