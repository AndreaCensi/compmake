**Compmake** is a non-obtrusive module that provides Make--like facilities to a Python applciation, including:

- Minimal effort **parallelization**.
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

Please report any problem at: http://github.com/AndreaCensi/compmake/issues


Changelog
---------

* v3.4.0 - Changed the way that dynamic job IDs are generated to avoid a race condition in a corner case.
* v3.3.7 - Bug fix.
* v3.3.6 - Experimental multyvac backend.

