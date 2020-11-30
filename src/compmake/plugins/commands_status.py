from compmake.events import register_handler
from compmake.state import get_compmake_config
from compmake.ui.visualization import ui_error, ui_info
from zuper_commons.text import indent


# TODO: command-succeeded: {'command': '
# command-interrupted: {'reason': 'KeyboardInterrupt', 'command': 'ls todo'}
def command_interrupted(context, event):
    c = event.kwargs["command"]
    traceback = event.kwargs["traceback"]
    ui_error(context, f"Command {c!r} interrupted.")
    ui_error(context, traceback)


register_handler("command-interrupted", command_interrupted)


def command_failed(context, event):
    c = event.kwargs["command"]
    r = event.kwargs["reason"]
    ui_error(context, f"Command {c!r} failed: {r}")


register_handler("command-failed", command_failed)

# my_prefix = '(plugin commands_status) '
my_prefix = ""


def command_line_interrupted(context, event):
    # Only write something if it is more than one
    command = event.kwargs["command"]
    if not ";" in command:
        return
    ui_error(context, my_prefix + f"Command sequence {command!r} interrupted.")


register_handler("command-line-interrupted", command_line_interrupted)


def command_line_failed(context, event):
    # Only write something if it is more than one
    command = event.kwargs["command"]
    if not ";" in command:
        return
    ui_error(context, my_prefix + f"Command sequence {command!r} failed.")


register_handler("command-line-failed", command_line_failed)


def job_failed(context, event):
    yes = get_compmake_config("details_failed_job")
    if not yes:
        return
    job_id = event.kwargs["job_id"]
    reason = event.kwargs["reason"]
    bt = event.kwargs["bt"]

    msg = f"Job {job_id!r} failed:"
    # s = reason.strip
    # if get_compmake_config('echo'):
    #     s += '\n' + bt
    msg += "\n" + indent(reason.strip(), "| ")

    # if get_compmake_config("echo"):
    #     s = bt.strip()
    #     msg += "\n" + indent(s, "> ")
    # else:
    #     msg += '\nUse "config echo 1" to have errors displayed.'
    msg += f'\nWrite "details {job_id}" to inspect the error.'
    ui_error(context, my_prefix + msg)


register_handler("job-failed", job_failed)


def job_interrupted(context, event):
    ui_error(
        context,
        my_prefix + "Job %r interrupted:\n %s" % (event.kwargs["job_id"], indent(event.kwargs["bt"], "> ")),
    )


register_handler("job-interrupted", job_interrupted)


def compmake_bug(context, event):
    ui_error(context, my_prefix + event.kwargs["user_msg"])
    ui_error(context, my_prefix + event.kwargs["dev_msg"])


register_handler("compmake-bug", compmake_bug)


# We ignore some other events; otherwise they will be catched
# by the default handler
def ignore(context, event):
    pass


register_handler("command-starting", ignore)
register_handler("command-line-starting", ignore)
register_handler("command-line-failed", ignore)
register_handler("command-line-succeeded", ignore)
register_handler("command-line-interrupted", ignore)

register_handler("manager-phase", ignore)

register_handler("parmake-status", ignore)

register_handler("job-succeeded", ignore)
register_handler("job-interrupted", ignore)

if True:  # debugging
    register_handler("worker-status", ignore)
    register_handler("manager-job-done", ignore)
    register_handler("manager-job-failed", ignore)
    register_handler("manager-job-processing", ignore)


def manager_succeeded(context, event):
    if event.kwargs["nothing_to_do"]:
        ui_info(context, "Nothing to do.")
    else:
        ntargets = len(event.kwargs["all_targets"])
        ndone = len(event.kwargs["done"])
        nfailed = len(event.kwargs["failed"])
        nblocked = len(event.kwargs["blocked"])
        if ntargets:
            s = f"Processed {ntargets} jobs ("
            ss = []
            if ndone:
                ss.append(f"{ndone} done")
            if nfailed:
                ss.append(f"{nfailed} failed")
            if nblocked:
                ss.append(f"{nblocked} blocked")
            s += ", ".join(ss)
            s += ")."
            if nfailed:
                ui_error(context, s)
            else:
                ui_info(context, s)


register_handler("manager-succeeded", manager_succeeded)  # TODO: maybe write sth
