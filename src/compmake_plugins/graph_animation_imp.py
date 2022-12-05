import os

from compmake import COMMANDS_ADVANCED, Context, Event, register_handler, ui_command
from zuper_commons.fs import make_sure_dir_exists
from .graph import graph


class Global:
    step = 0
    job_list = []
    graph_params = {}
    dirname = "."

    size = (None, None)
    dpi = None
    processing = set()


async def update_graph(context: Context, event: Event):
    print("event: %s" % event)

    if event.name in ["manager-job-processing"]:
        job_id = event.kwargs["job_id"]
        Global.processing.add(job_id)
    if event.name in ["manager-job-failed", "manager-job-done"]:
        job_id = event.kwargs["job_id"]
        Global.processing.remove(job_id)

    print(f"global processing {Global.processing}")
    if "job_id" in event.kwargs:
        what = f"{event.name}-{event.kwargs['job_id']}"
    else:
        what = event.name
    filename = os.path.join(Global.dirname, f"step-{Global.step:04d}-{what}")

    make_sure_dir_exists(filename)
    #     print('step %d: jobs = %s' % (Global.step, Global.job_list))
    await graph(
        job_list=list(Global.job_list),
        context=context,
        filename=filename,
        processing=Global.processing,
        **Global.graph_params,
    )
    Global.step += 1

    # see here:
    # http://stackoverflow.com/questions/14784405/how-to-set-the-output-size-in-graphviz-for-the-dot-format

    png = filename + ".png"
    png2 = filename + "-x.png"

    size = Global.size
    dpi = Global.dpi
    # noinspection PyUnresolvedReferences
    cmd0 = [
        "dot",
        "-Tpng",
        "-Gsize=%s,%s\!" % (size[0] / dpi, size[1] / dpi),
        "-Gdpi=%s" % dpi,
        "-o" + png,
        filename,
    ]
    from system_cmd import system_cmd_result

    system_cmd_result(".", cmd0, display_stdout=True, display_stderr=True, raise_on_error=True)

    cmd = [
        "convert",
        png,
        "-gravity",
        "center",
        "-background",
        "white",
        "-extent",
        "%sx%s" % (size[0], size[1]),
        png2,
    ]
    system_cmd_result(".", cmd, display_stdout=True, display_stderr=True, raise_on_error=True)
    os.unlink(png)


@ui_command(section=COMMANDS_ADVANCED, alias="graph-animation")
def graph_animation(
    job_list, context, dirname="compmake-graph-animation", dpi=150, width=900, height=900, label="function"
):
    """
    Runs a step-by-step animation.

    Registers the handlers. Then call 'make' or 'parmake'.
    """
    possible = ["none", "id", "function"]
    if not label in possible:
        msg = "Invalid label method %r not in %r." % (label, possible)
        raise ValueError(msg)

    Global.dirname = dirname
    Global.job_list = list(job_list)

    Global.graph_params = dict(filter="dot", format="png", label=label, color=True, cluster=True)
    Global.dpi = dpi
    Global.size = (width, height)
    Global.processing = set()
    events = [
        "manager-job-processing",
        "manager-job-failed",
        "manager-job-done",
        "manager-succeeded",
        "manager-phase",
    ]

    for e in events:
        register_handler(e, update_graph)
