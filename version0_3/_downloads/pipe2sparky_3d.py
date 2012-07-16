#! /usr/bin/env python

import nmrglue as ng

# read in the varian data
dic,data = ng.pipe.read_lowmem("../common_data/3d_pipe/ft/test%03d.ft3")

# Set the parameters 
u = ng.pipe.guess_udic(dic,data)

# create the converter object and initilize with varian data
C = ng.convert.converter()
C.from_pipe(dic,data,u)

# create pipe data and then write it out
ng.sparky.write("3d_sparky.ucsf",*C.to_sparky(),overwrite=True)

# check the conversion against NMRPipe
print "Conversion complete, listing differences between files:"
sdic,sdata = ng.sparky.read_lowmem("3d_sparky.ucsf")
sdic2,sdata2 = ng.sparky.read_lowmem("../common_data/3d_sparky/data.ucsf")
print ng.misc.pair_similar(sdic,sdata[5],sdic2,sdata2[5],verb=True)
