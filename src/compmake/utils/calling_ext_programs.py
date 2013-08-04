from system_cmd import *  # @UnusedWildImport

# 
# import subprocess
# import tempfile
# import sys
# import os
# from contracts.utils import indent
# 
# __all__ = ['system_cmd_result', 'CmdResult', 'CmdException']
# 
# 
# class CmdResult(object):
#     def __init__(self, cwd, cmd, ret, rets, interrupted, stdout, stderr):
#         self.cwd = cwd
#         self.cmd = cmd
#         self.ret = ret
#         self.rets = rets
#         self.stdout = stdout
#         self.stderr = stderr
#         self.interrupted = interrupted
# 
#     def __str__(self):
#         msg = ('The command: %s\n'
#                '     in dir: %s\n' % (self.cmd, self.cwd))
# 
#         if self.interrupted:
#             msg += 'Was interrupted by the user\n'
#         else:
#             msg += 'returned: %s' % self.ret
#         if self.rets is not None:
#             msg += '\n' + indent(self.rets, 'error>')
#         if self.stdout:
#             msg += '\n' + indent(self.stdout, 'stdout>')
#         if self.stderr:
#             msg += '\n' + indent(self.stderr, 'stderr>')
#         return msg
# 
# 
# class CmdException(Exception):
#     def __init__(self, cmd_result):
#         Exception.__init__(self, cmd_result)
#         self.res = cmd_result
# 
#     def __str__(self):
#         return self.res.__str__()
# 
# 
# def system_cmd_result(cwd, cmd,
#                       display_stdout=False,
#                       display_stderr=False,
#                       raise_on_error=False,
#                       write_stdin='',
#                       capture_keyboard_interrupt=False):  # @UnusedVariable
#     ''' 
#         Returns the structure CmdResult; raises CmdException.
#         Also OSError are captured.
#         KeyboardInterrupt is passed through unless specified
#         
#         :param write_stdin: A string to write to the process.
#     '''
#     tmp_stdout = tempfile.TemporaryFile()
#     tmp_stderr = tempfile.TemporaryFile()
# 
#     ret = None
#     rets = None
#     interrupted = False
# 
#     try:
#         stdout = None if display_stdout else tmp_stdout.fileno()
#         stderr = None if display_stderr else tmp_stderr.fileno()
#         p = subprocess.Popen(
#                 cmd2args(cmd),
#                 stdin=subprocess.PIPE,
#                 stdout=stdout,
#                 stderr=stderr,
#                 cwd=cwd)
# 
#         if write_stdin != '':
#             p.stdin.write(write_stdin)
#             p.stdin.flush()
#         p.stdin.close()
#         p.wait()
#         ret = p.returncode
#         rets = None
#         interrupted = False
#     except KeyboardInterrupt:
#         ret = 100
#         interrupted = True
#     except OSError as e:
#         interrupted = False
#         ret = 200
#         rets = str(e)
# 
#     # remember to go back
#     def read_all(f):
#         os.lseek(f.fileno(), 0, 0)
#         return f.read()
# 
#     res = CmdResult(cwd, cmd, ret, rets, interrupted,
#                     stdout=read_all(tmp_stdout),
#                     stderr=read_all(tmp_stderr))
# 
#     if raise_on_error:
#         if res.ret != 0:
#             raise CmdException(res)
# 
#     return res
# 
# 
# def cmd2args(s):
#     ''' if s is a list, leave it like that; otherwise split()'''
#     if isinstance(s, list):
#         return s
#     elif isinstance(s, str):
#         return s.split()
#     else:
#         assert False
# 
# if __name__ == '__main__':
#     cwd = '.'
#     cmd = " ".join(sys.argv[1:])
#     cmd = cmd.strip()
#     if not cmd:
#         print('No command given.')
#     else:
#         try:
#             display = False
#             res = system_cmd_result(cwd, cmd,
#                           display_stdout=display,
#                           display_stderr=display,
#                           raise_on_error=True)
#             print('Succeed: %s' % res)
#         except CmdException as e:
#             print('Exception: %s' % e)

