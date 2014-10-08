#!/bin/bash
set -x
set -e
comp="compmake --colorize False --readline False"
for module in using_compmake1 using_compmake2 using_compmake3; do
	echo 'exit' | python $module.py
	$comp  out-${module} -c "clean"
	
	bname=`basename ${module} .py`
	output=${bname}_list_before.txt
	echo "@: ls" > $output
	$comp out-${module} -c "ls" | head -n 6 >> $output
	echo "[...]" >> $output
	
	$comp out-${module} -c "make" > ${bname}_make.txt  2>&1 
	$comp  out-${module} -c "make" > ${bname}_make2.txt 2>&1

	for m in make make2; do
		input=${bname}_${m}.txt
		output=${bname}_${m}_snip.txt
		num=5
		cat $input | grep done | uniq | head -n $num  > $output
		echo "[...] " >>  $output
		cat $input | grep done | uniq | tail -n $num  >> $output	
	done
done


module=using_compmake1
 
$comp out-${module} -c clean
echo "@: ls " > list_before.txt
$comp out-${module} -c ls | head -n 6 >> list_before.txt
echo "[...]" >> list_before.txt
$comp out-${module} -c "graph filename=graph_before"
$comp out-${module} -c "graph compact=1 filename=graph_before_compact"

$comp out-${module} -c make 
echo "@: ls " > list_after.txt
$comp  out-${module} -c list | head -n 6 >> list_after.txt
echo "[...]" >> list_after.txt
$comp out-${module} -c "graph filename=graph_after"
$comp out-${module} -c "graph compact=1 filename=graph_after_compact"


$comp  out-${module} -c "clean funcB-*"
$comp  out-${module} -c "graph filename=graph3"

# just for the prompt
echo "$ compmake out-example " > prompt.txt
echo | $comp  out-${module} | head -n 3 >> prompt.txt
echo "@:" >> prompt.txt

#make -C .. html
