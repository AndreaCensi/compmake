#!/usr/bin/env python

from system_cmd import system_cmd_show
import compmake
import shutil
import os


def go(filename, cm_cmd, video_name):
    dirname=video_name
    out = '%s.mp4' % video_name
    if os.path.exists(dirname):
        shutil.rmtree(dirname)
    if os.path.exists(out):
        os.unlink(out)
    cmd1 = ['python', filename, 
            "clean; graph-animation dirname=%s; %s" % (dirname, cm_cmd)]
    system_cmd_show('.', cmd1)
    cmd2 = ['pg-video-join',
            '-d', dirname,
            '-p', '.*.png',
            '--fps', '5',
            '-o', out]
    os.unlink(out + '.metadata.yaml')
    system_cmd_show('.', cmd2)
    
    

if __name__ == '__main__':
    context = compmake.Context()
    context.comp(go, '../example_simple.py', 
                 'make', 'anim-simple-make')
    context.comp(go, '../example_simple.py', 
                 'parmake n=2', 'anim-simple-parmake2')
    context.batch_command('parmake')