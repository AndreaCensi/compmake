#!/bin/bash
set -x
set -e

for module in using_compmake1 using_compmake2 using_compmake3; do
	echo 'exit' | python $module.py
	compmake --colorize False  out-${module} -c "clean"
	
	bname=`basename ${module} .py`
	output=${bname}_list_before.txt
	echo "$ compmake example ls" > $output
	compmake --colorize False   out-${module} -c "ls" | head -n 6 >> $output
	echo "    [...]" >> $output
	
	compmake --colorize False   out-${module} -c "make" > ${bname}_make.txt  2>&1 
	compmake --colorize False   out-${module} -c "make" > ${bname}_make2.txt 2>&1

	for m in make make2; do
		input=${bname}_${m}.txt
		output=${bname}_${m}_snip.txt
		num=5
		cat $input | grep done | uniq | head -n $num  > $output
		echo "    [...] " >>  $output
		cat $input | grep done | uniq | tail -n $num  >> $output	
	done
done


module=using_compmake1

compmake out-${module} -c clean
echo "$ compmake out-example -c ls" > list_before.txt
compmake --colorize False   out-${module} -c ls | head -n 6 >> list_before.txt
echo "[...]" >> list_before.txt
compmake  out-${module} -c "graph filename=graph_before"
compmake  out-${module} -c "graph compact=1 filename=graph_before_compact"

compmake  out-${module} -c make 
echo "$ compmake out-example -c ls" > list_after.txt
compmake --colorize False   out-${module} -c list | head -n 6 >> list_after.txt
echo "[...]" >> list_after.txt
compmake  out-${module} -c "graph filename=graph_after"
compmake  out-${module} -c "graph compact=1 filename=graph_after_compact"


compmake  out-${module} -c "clean funcB-*"
compmake  out-${module} -c "graph filename=graph3"


# just for the prompt
echo "$ compmake out-example " > prompt.txt
echo | compmake  out-${module} --colorize False | head -n 3 >> prompt.txt
echo "@:" >> prompt.txt

#make -C .. html
