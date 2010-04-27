#!/bin/bash
#set -e

compmake using_compmake1 clean
compmake using_compmake1 list | head -n 10 > list_before.txt
echo "[...]" >> list_before.txt
compmake using_compmake1 graph filename=graph_before

compmake using_compmake1 make 
compmake using_compmake1 list | head -n 10 > list_after.txt
echo "[...]" >> list_after.txt
compmake using_compmake1 graph filename=graph_after


