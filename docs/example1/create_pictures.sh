#!/bin/bash
set -e

compmake using_compmake1 clean
compmake --colorize False  using_compmake1 list | head -n 6 > list_before.txt
echo "[...]" >> list_before.txt
compmake using_compmake1 graph filename=graph_before

compmake using_compmake1 make 
compmake --colorize False  using_compmake1 list | head -n 6 > list_after.txt
echo "[...]" >> list_after.txt
compmake using_compmake1 graph filename=graph_after

compmake using_compmake1 clean func2-\*
compmake using_compmake1 graph filename=graph3

#make -C .. html
