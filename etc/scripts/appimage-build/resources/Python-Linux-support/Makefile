# Current director
PROJECT_DIR=$(shell pwd)

BUILD_NUMBER=custom

# Version of packages that will be compiled by this meta-package
# PYTHON_VERSION is the full version number (e.g., 3.10.0b3)
# PYTHON_MICRO_VERSION is the full version number, without any alpha/beta/rc suffix. (e.g., 3.10.0)
# PYTHON_VER is the major/minor version (e.g., 3.10)
PYTHON_VERSION=3.10.9
PYTHON_MICRO_VERSION=$(shell echo $(PYTHON_VERSION) | grep -Po "\d+\.\d+\.\d+")
PYTHON_VER=$(basename $(PYTHON_VERSION))

ARCH=$(shell uname -m)

all:
	@echo "***** Building $(PYTHON_VERSION) $(ARCH) build $(BUILD_NUMBER) *****"
	rm -rf build
	docker build -t beeware/python-linux-$(ARCH)-support .
	docker run -e \
		BUILD_NUMBER=$(BUILD_NUMBER) \
		-v $(PROJECT_DIR)/downloads:/local/downloads \
		-v $(PROJECT_DIR)/dist:/local/dist \
		-v $(PROJECT_DIR)/build:/local/build \
		beeware/python-linux-$(ARCH)-support

# Clean all builds
clean:
	rm -rf build dist

# Full clean - includes all downloaded products
distclean: clean
	rm -rf downloads

dependencies:
	dpkg -l > downloads/system.versions

downloads: downloads/Python-$(PYTHON_VERSION).tgz dependencies

###########################################################################
# Python
###########################################################################

# Download original Python source code archive.
downloads/Python-$(PYTHON_VERSION).tgz:
	mkdir -p downloads
	if [ ! -e downloads/Python-$(PYTHON_VERSION).tgz ]; then \
		curl --fail -L https://www.python.org/ftp/python/$(PYTHON_MICRO_VERSION)/Python-$(PYTHON_VERSION).tgz \
			-o downloads/Python-$(PYTHON_VERSION).tgz; \
	fi

build:
	mkdir build

dist:
	mkdir dist

build/Python-$(PYTHON_VERSION)/Makefile: build downloads
	@echo "***** Building $(PYTHON_VERSION) $(ARCH) build $(BUILD_NUMBER) *****"
	# Unpack target Python
	cd build && tar zxf ../downloads/Python-$(PYTHON_VERSION).tgz

	# Configure target Python
	cd build/Python-$(PYTHON_VERSION) && ./configure \
		--prefix=$(PROJECT_DIR)/build/python \
		--enable-ipv6 \
		--enable-shared \
		2>&1 | tee -a ../python-$(PYTHON_VERSION).config.log

build/Python-$(PYTHON_VERSION)/python.exe: build/Python-$(PYTHON_VERSION)/Makefile
	cd build/Python-$(PYTHON_VERSION) && \
		make \
			2>&1 | tee -a ../python-$(PYTHON_VERSION).build.log

build/python/bin/python$(PYTHON_VER): build/Python-$(PYTHON_VERSION)/python.exe
	cd build/Python-$(PYTHON_VERSION) && \
		make install \
			2>&1 | tee -a ../python-$(PYTHON_VERSION).install.log
	# Make the binary and libpython3.so relocatable
	patchelf --set-rpath "\$$ORIGIN/../lib" build/python/bin/python$(PYTHON_VER)
	patchelf --set-rpath "\$$ORIGIN" build/python/lib/libpython3.so

build/python/VERSIONS: dependencies
	echo "Python version: $(PYTHON_VERSION) " > build/python/VERSIONS
	echo "Build: $(BUILD_NUMBER)" >> build/python/VERSIONS
	echo "---------------------" >> build/python/VERSIONS
	echo "BZip2: $$(awk '$$2=="bzip2" { print $$3 }' downloads/system.versions)" >> build/python/VERSIONS
	echo "OpenSSL: $$(awk '$$2=="openssl" { print $$3 }' downloads/system.versions)" >> build/python/VERSIONS
	echo "XZ: $$(awk '$$2=="liblzma5:amd64" { print $$3 }' downloads/system.versions)" >> build/python/VERSIONS

dist/Python-$(PYTHON_VER)-linux-$(ARCH)-support.$(BUILD_NUMBER).tar.gz: dist build/python/bin/python$(PYTHON_VER) build/python/VERSIONS
	tar zcvf $@ -X exclude.list -C build/python `ls -A build/python`

Python: dist/Python-$(PYTHON_VER)-linux-$(ARCH)-support.$(BUILD_NUMBER).tar.gz
