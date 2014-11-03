#!/usr/bin/env python

from system_cmd import system_cmd_result, system_cmd_show
import compmake
import os
import shutil


def go(filename, cm_cmd, video_name, width=800, height=250, dpi=100, label='id'):
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
            "clean; graph-animation label=%s width=%s height=%s dpi=%s dirname=%s; %s" %
             (label, width, height, dpi, reldir, cm_cmd)]
    
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
    
    cases = {
      'simplest': dict(script='example_simplest.py'),
      'fail': dict(script='example_fail.py'),
      'dynamic': dict(script='example_dynamic.py'),
      'recursion': dict(script='example_recursion.py',
                             params=dict(width=1000, height=400)),
             
      'reduce_linear': dict(script='reduce_linear.py',
                            params=dict(width=400, height=1000)),
      'reduce_rec': dict(script='reduce_rec.py',
                            params=dict(width=1000, height=600)),
    
    }
    
    methods = {
        'make': dict(cmd='make recurse=1'),
        'parmake4': dict(cmd='parmake recurse=1 n=4'),
        'parmake16': dict(cmd='parmake recurse=1 n=16'),
    }
    
    visualizations = {
        'none': dict(label='none'),
        'id': dict(label='id'),
        'function': dict(label='function'),
    }
    
    for case in cases:
        script = cases[case]['script']
        params = cases[case].get('params', {})
        
        for method in methods:
            cmd = methods[method]['cmd']
        
            for vis in visualizations:
                all_params = {}
                all_params.update(params)
                all_params.update(visualizations[vis]) 
                
                name = 'anim-%s-%s-%s' % (case, method, vis)
                outdir = os.path.join('results', name)
                if not os.path.exists(outdir):
                    os.makedirs(outdir)
                context.comp(go,script, cmd, outdir, 
                             job_id=name, **all_params)
 

    context.compmake_console()