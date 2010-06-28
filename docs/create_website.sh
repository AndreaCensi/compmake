convert initial_picture.001.png -trim +repage -transparent '#cccccc' initial-with.png  
convert initial_picture.002.png -trim +repage -transparent '#cccccc' initial.png  
compmake --slave default commands_html > commands_list.html 
compmake --slave default config_html > config_list.html 
sphinx-build -a -b html . website

# cp website/index.html website/index2.html
# cp website/coming_soon.html website/index.html

