

Details on job execution
------------------------


Compmake uses a greedy approach to job scheduling. Define as "top targets" the jobs upon which there are no dependencies. the assumption is that the top target are the ones that the user is interested in. Therefore, at each time, compmake chooses to execute the readt job which is closer o a top target.

More in detail, assume that each job has a ``priority``, a nonpositive integer associated to it. 
This is defined as minus the distance of a job to a top target.

We can compute the priority recursively as follows.
For jobs without parents (top targets), we define the priority as 0: ::

	parents(job) = []  =>  priority(job) = 0
	
For jobs with parents, we use the following formula: ::

	priority(job) =  -1 + max_{p in parent(job)} (priority(p))

Note that we take the max, because we want the shortest path to the top.

Also note that we consider only the parents contained in targets.
