""" Implements the initial and final banner """

from compmake import all_jobs, compmake_colored, Context, Event, register_handler, version

compmake_issues_url = "http://github.com/AndreaCensi/compmake/issues"
name = "Compmake"


# banners = [
#     "Tame your Python computations!",
#     "Keep calm and carry on",
# ]


async def console_starting(context: Context):
    db = context.get_compmake_db()

    # # starting console
    # def printb(s):
    #     print(pad_to_screen(s))

    #     random_banner = random.choice(banners)
    #     banner = "   ``%s,," % random_banner
    #     # banner_s = compmake_colored(banner, 'cyan')

    version_string = "%s %s" % (
        compmake_colored(name, attrs=["bold"]),
        compmake_colored(version, attrs=["bold"]),
    )

    # printb("Welcome to the Compmake console. ")
    njobs = len(list(all_jobs(db)))
    # printb(version_string + ("  (%d jobs loaded)" % njobs) + banner_s)
    await context.write_message_console(version_string + ("  (%d jobs loaded)" % njobs))


async def console_ending(context: Context, event: Event) -> None:
    url = compmake_colored(compmake_issues_url, attrs=["bold"])
    msg = f"Thanks for using Compmake. Please report problems to {url}"  #

    await context.write_message_console(msg)  # keep print # XXX: cannot see anymore?


register_handler("console-starting", console_starting)
register_handler("console-ending", console_ending)
