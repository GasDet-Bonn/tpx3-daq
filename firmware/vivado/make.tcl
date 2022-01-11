
# -----------------------------------------------------------
# Copyright (c) SILAB , Physics Institute, University of Bonn
# -----------------------------------------------------------
#
#   This script creates Vivado projects and bitfiles for the supported hardware platforms
#
#   Start vivado in tcl mode by typing:
#       vivado -mode tcl -source ../vivado/make.tcl
#       openocd  -f ../vivado/numato_mimasa7.cfg -c "init" -c "pld load 0 output/tpx3-daq-mimasA7.bit" -c "shutdown"
#

if { [info exists ::env(PYTHONPATH)] } {
    unset ::env(PYTHONPATH)
}

if { [info exists ::env(PYTHONHOME)] } {
    unset ::env(PYTHONHOME)
}

set basil_dir [exec python -c "import basil, os; print(os.path.dirname(basil.__file__))"]
set firmware_dir [exec python -c "import os; print(os.path.dirname(os.getcwd()))"]

set include_dirs [list $basil_dir/firmware/modules $basil_dir/firmware/modules/utils $firmware_dir]

file mkdir output reports

proc read_design_files {} {

    global firmware_dir
    read_verilog $firmware_dir/src/tpx3_mimasA7.v
    read_edif $firmware_dir/lib/SiTCP_Netlist_for_Artix7/SiTCP_XC7A_32K_BBT_V110.ngc
}

proc run_bit { part board xdc_file} {
    create_project -force -part $part $board designs
    read_design_files
    read_xdc $xdc_file

    generate_target -verbose -force all [get_ips]

    global include_dirs

    synth_design -top tpx3_daq -include_dirs $include_dirs -verilog_define "SYNTHESIS=1"
    opt_design
    place_design
    phys_opt_design
    route_design
    report_utilization
    report_timing -file "reports/report_timing.$board.log"
    write_bitstream -force -file output/${board}
    
    #write_cfgmem -format mcs -size $size -interface SPIx1 -loadbit "up 0x0 output/$board.bit" -force -file output/$board
    #write_cfgmem -force -format bin -interface spix4 -size 16 -loadbit "up 0x0 output/$board.bit" -file output/$board.bin

    close_project
}

#########

#
# Create projects and bitfiles
#

#       FPGA type           board name	                   constraints file 
run_bit xc7a50t-fgg484-1   tpx3-daq-mimasA7          $firmware_dir/src/mimasA7.xdc

exit
