from zuper_commons.logs import ZLogger, ZLoggerInterface

logger: ZLoggerInterface = ZLogger(__name__)
from .commands import *
