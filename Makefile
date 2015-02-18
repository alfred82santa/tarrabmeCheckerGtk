
MEDIA_DIR = media
CONFIG_DIR = config

SRC_DIR = src
APPLICATION_EXE = application.py

RESOURCE_COMPILER = glib-compile-resources
RESOURCE_XML_FILE = tarrabme-checker-resources.xml

CONFIG_COMPILER = glib-compile-schemas


help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  clean         to clean python cache files"
	@echo "  buildconfig   to build config files"
	@echo "  buildresource to build resource media files"
	@echo "  buildall      to build config and resource media files"
	@echo "  run           to run application"

clean:
	@echo "Removing all *.pyc files."
	find . -name '*.pyc' -exec rm -f {} +
	@echo "Removing all *.pyo files."
	find . -name '*.pyo' -exec rm -f {} +
	# python 3
	@echo "Removing all __pycache__ directories."
	find . -name '__pycache__' -exec rm -rf {} +

buildconfig:
	@echo "Building configurations..."
	$(CONFIG_COMPILER) $(CONFIG_DIR)
	@echo "Build finished."

buildresource:
	@echo "Building resources..."
	$(RESOURCE_COMPILER) $(MEDIA_DIR)/$(RESOURCE_XML_FILE) --sourcedir=$(MEDIA_DIR)
	@echo "Build finished."

buildall:
	$(MAKE) buildconfig
	$(MAKE) buildresource

run:
	$(SRC_DIR)/$(APPLICATION_EXE)

buildrun:
	$(MAKE) buildall
	$(MAKE) run
