compmake --slave commands_html > commands_list.html 
compmake --slave config_html > config_list.html 
sphinx-build -a -b html . website

cp website/index.html website/index2.html
cp website/coming_soon.html website/index.html

