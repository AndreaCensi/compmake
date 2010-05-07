#!/bin/bash
set -e

module=using_compmake1

compmake ${module} clean
compmake --colorize False   ${module} list | head -n 6 > list_before.txt
echo "[...]" >> list_before.txt
compmake  ${module} graph filename=graph_before
compmake  ${module} graph compact=1 filename=graph_before_compact

compmake  ${module} make 
compmake --colorize False   ${module} list | head -n 6 > list_after.txt
echo "[...]" >> list_after.txt
compmake  ${module} graph filename=graph_after
compmake  ${module} graph compact=1 filename=graph_after_compact


compmake  ${module} clean func2-\*
compmake  ${module} graph filename=graph3

#make -C .. html
