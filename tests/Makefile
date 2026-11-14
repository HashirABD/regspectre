SIM ?= icarus
TOPLEVEL_LANG ?= verilog
VERILOG_SOURCES = $(shell pwd)/../rtl/w1c_smoke.sv
COCOTB_TOPLEVEL = w1c_smoke
COCOTB_TEST_MODULES = test_smoke
COMPILE_ARGS += -g2012
include $(shell cocotb-config --makefiles)/Makefile.sim
