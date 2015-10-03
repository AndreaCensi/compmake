Compmake
===============================================

**Compmake** is an unobstrusive Python library that provides 
Make--like facilities to a Python application, including:

- Minimal effort job management and **parallelization** 
(multiple CPU on a single host, cluster computing using SGE, 
and experimental support for cloud computing using Multyvac).
- **Caching** of temporary results: you can interrupt your program 
and restart it without losing what was already computed.
- **Failure tolerance**: if a job fails, other jobs that do
not depend on it continue to be executed.
- A **console** for inspecting failures and partial completion,
with familiar commands such as ``make``, ``clean``, etc.

Please see the manual at:

http://purl.org/censi/compmake-manual

<a style="display: block; float: left" href="http://purl.org/censi/compmake-manual">
    <img style="float: left; border: solid 1px red" src="docs/source/my_static/2015-compmake-v3.png"/>
</a>




Issues
------

Please report any problem using Github's issue tracker at

   http://github.com/AndreaCensi/compmake/issues


Acknowledgements
----------------

Your tax dollars at work! Compmake's development was supported 
by the [National Science Foundation](http://www.nsf.gov/)
in the *National Robotics Initiative* program under grant #1405259.


Screencasts
---------------------------------

* Screencast 1: [Compmake overview](http://purl.org/censi/compmake-overview)
* Screencast 2: [Compmake basic usage](http://purl.org/censi/compmake-basics)
* Screencast 3: [Compmake + Multyvac](http://purl.org/censi/compmake-multyvac)
* Screencast 4: [Compmake + SGE](http://purl.org/censi/compmake-sge)

* [Demo with images used in the screencasts](https://github.com/AndreaCensi/compmake-demo-images/)


Some animations of the job graph
---------------------------------

*Robustness to job failure*

<img src="http://purl.org/censi/research/201410-compmake-animations/anim-fail-make-function.gif"/>

*Simple dynamic jobs*

<img src="http://purl.org/censi/research/201410-compmake-animations/anim-dynamic-make-function.gif"/>

*Dynamic jobs and recursive parallel executions*

<img src="http://purl.org/censi/research/201410-compmake-animations/anim-recursion-parmake16-none.gif"/>



Changelog
---------

* v3.5 - Added ``why`` command --- compact error visualization. Removed 
  color effects which might not be suitable for all console types.
* v3.4.1 - Bug fix; experimental multyvac_sync
* v3.4.0 - Changed the way that dynamic job IDs are generated 
           to avoid a race condition in a corner case.
* v3.3.7 - Bug fix.
* v3.3.6 - Experimental Multyvac backend.


