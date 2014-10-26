#!/usr/bin/env python

from system_cmd import system_cmd_result, system_cmd_show
import compmake
import os
import shutil


def go(filename, cm_cmd, video_name):
    dirname=video_name
    out = '%s.mp4' % video_name
    if os.path.exists(dirname):
        shutil.rmtree(dirname)
    if os.path.exists(out):
        os.unlink(out)
    
    reldir = 'animation'
    animdir = os.path.join(dirname, reldir)
    if not os.path.exists(animdir):
        os.makedirs(animdir)
        
    cmd1 = ['python', os.path.realpath(filename), 
            "clean; graph-animation dirname=%s; %s" % (reldir, cm_cmd)]
    
    print(dirname, cmd1)
    system_cmd_result(
            dirname, cmd1,
            display_stdout=True,
            display_stderr=True,
            raise_on_error=False)
    
    cmd2 = ['pg-video-join',
            '-d', animdir,
            '-p', '.*.png',
            '--fps', '5',
            '-o', out]
    
    system_cmd_show('.', cmd2)
    
    metadata = out + '.metadata.yaml'
    if os.path.exists(metadata):
        os.unlink(metadata)
    
    
    

if __name__ == '__main__':
    context = compmake.Context()
    context.comp(go, 'example_simplest.py', 'make', 
                 'anim-simplest-make',
                 job_id='anim-simplest-make')
    context.comp(go, 'example_simplest.py', 'parmake n=2', 
                 'anim-simplest-parmake2',
                 job_id='anim-simplest-parmake2')
    context.comp(go, 'example_fail.py', 'make', 
                 'anim-fail-make',
                 job_id='anim-fail-make')
    context.compmake_console()