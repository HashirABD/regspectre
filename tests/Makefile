SIM ?= icarus
TOPLEVEL_LANG ?= verilog
COMPILE_ARGS += -g2012

TARGET ?= uart_ctrl

ifeq ($(TARGET),w1c_smoke)
VERILOG_SOURCES = $(shell pwd)/../rtl/w1c_smoke.sv
COCOTB_TOPLEVEL = w1c_smoke
COCOTB_TEST_MODULES = test_smoke
else ifeq ($(TARGET),uart_ctrl)
VERILOG_SOURCES = $(shell pwd)/../rtl/uart_ctrl.sv
COCOTB_TOPLEVEL = uart_ctrl
COCOTB_TEST_MODULES = test_uart_ctrl,test_bus_driver,test_demo,test_pbt_hw_timing,test_pbt_negative_control
endif

export PYTHONPATH := $(shell pwd)/..:$(PYTHONPATH)
include $(shell cocotb-config --makefiles)/Makefile.sim