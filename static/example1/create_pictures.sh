#!/bin/bash
# set -e

for module in using_compmake1 using_compmake2 using_compmake3; do
	compmake --colorize False   ${module} -c "clean"
	

	bname=`basename ${module} .py`
	output=${bname}_list_before.txt
	echo "$ compmake example list" > $output
	compmake --colorize False   ${module} -c "list" | head -n 6 >> $output
	echo "    [...]" >> $output
	
	
	compmake --colorize False   ${module} -c "make" > ${bname}_make.txt  2>&1 
	compmake --colorize False   ${module} -c "make" > ${bname}_make2.txt 2>&1

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

compmake ${module} -c clean
echo "$ compmake example -c list" > list_before.txt
compmake --colorize False   ${module} -c list | head -n 6 >> list_before.txt
echo "[...]" >> list_before.txt
compmake  ${module} -c "graph filename=graph_before"
compmake  ${module} -c "graph compact=1 filename=graph_before_compact"

compmake  ${module} -c make 
echo "$ compmake example -c list" > list_after.txt
compmake --colorize False   ${module} -c list | head -n 6 >> list_after.txt
echo "[...]" >> list_after.txt
compmake  ${module} -c "graph filename=graph_after"
compmake  ${module} -c "graph compact=1 filename=graph_after_compact"


compmake  ${module} -c "clean func2-*"
compmake  ${module} -c "graph filename=graph3"


# just for the prompt
echo "$ compmake example " > prompt.txt
echo | compmake --colorize False ${module} | head -n 3 >> prompt.txt
echo "@:" >> prompt.txt

#make -C .. html
