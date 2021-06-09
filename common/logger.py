import os
import time
import logging, coloredlogs
from collections import OrderedDict
from configs import LOGGER_CONFIG_FILE, LOGS_DIR, if_not_create
from configs import get_configs_ordered as _logger_configs

'''
通过这个脚本中的内容我们可以实现在任何一个地方对整个系统的日志进行统一的输出
日志对象可以简单的通过GLogger类的get方法获得
通过GLogger生成的logging对象会首先从configs目录下寻找用户自定义的配置，若没有用户自定义的配置，则会使用默认的配置

对于每一个logging对象来说，都能够设置如下属性：
   - format
   - format_file
   - log_level
   - out_file   1. ""或"self" 是单独生成一个log文件，日志名称对应写类的时候，设置的name字段，
   　　　　　　　　　　若没有设置name字段，则默认使用“__module__.__name__.log”的名称（root例外），
   　　　　　　　 2. "xxx.log" 则会生成对应的log文件，如果发现两个class的log文件同名，则会共用一个文件
                3. 也可以设置为上面出现过的logging config名称
   　　　　      4. 不设置该项或者使用null则表示不输出日志文件
'''


class LoggerManager(object):
    __all_loggers = {}
    __all_files = {}

    def __init__(self, config_file):
        cf: OrderedDict = _logger_configs(config_file)
        __global = cf['global']
        self.LEVELS = __global['levels']
        self.LEVELS_DICT = {key: i for i, key in enumerate(self.LEVELS)}
        self.LOWEST_LEVEL = self.LEVELS_DICT[__global['lowest_level']]
        self.SHORT_NAME = __global['short_name']
        self.ALLOW_ABSTRACT = __global['allow_abstract']

        __default = cf['default']
        self.DEFAULT_LEVEL = self.LEVELS_DICT[__default['log_level']]
        self.LOGGING_FORMAT = __default['format']
        self.LOGGING_FORMAT_FILE = __default['format_file']
        self.DEFAULT_FILE = __default['out_file']

        self.TIME_STAMP = time.strftime('%Y%m%d_%H%M%S', time.localtime(time.time()))
        self.LOGS_DIR = os.path.join(LOGS_DIR, self.TIME_STAMP)

        __root = cf['root']
        self.level = __root['log_level']
        self.out_file = __root['out_file']
        self.name = __root['name']
        self.format = __root.get('format')
        self.format_file = __root.get('format_file')
        self._L = self._create_logger(self.name, level=self.level)
        if self.out_file is not None:
            _, fname, fh = self._create_file(self.out_file)
            self._L.addHandler(fh)
            self._L.debug('Create log file for root logger: %s', fname)
        self._L.debug('Create Root Logger successful')

        cf.pop('root')
        cf.pop('global')
        self.logger_configs = cf

    def _create_logger(self, name, level=None, fmt=None):
        if level is None:
            level = self.DEFAULT_LEVEL
        if isinstance(level, str):
            level = self.LEVELS_DICT[level]
        if (fmt is None) or (not isinstance(fmt, str)):
            fmt = self.LOGGING_FORMAT
        if self.SHORT_NAME:
            name = name.split('.')[-1]
        _L = logging.getLogger(name)
        coloredlogs.install(level=self.LEVELS[max(level, self.LOWEST_LEVEL)], logger=_L, fmt=fmt)
        self.__all_loggers[name] = _L
        return _L

    def _create_file(self, name, fmt=None, file_name=None):
        if file_name is None:
            file_name = '%s.log' % name
        elif not file_name.endswith('.log'):
            file_name += '.log'
        fh = self.__all_files.get(file_name)
        if fh is None:
            full_path = os.path.join(self.LOGS_DIR, file_name)
            if_not_create(self.LOGS_DIR)
            fh = logging.FileHandler(full_path, 'w')
            if fmt is None:
                fmt = self.LOGGING_FORMAT_FILE
            fh.setFormatter(logging.Formatter(fmt))
            self.__all_files[file_name] = fh
            return True, file_name, fh
        return False, file_name, fh

    def get(self, name, cls_name) -> logging.Logger:
        # 如果logger已经存在，则直接返回共享即可
        t = self.__all_loggers.get(name)
        if t is not None:
            self._L.debug('Logger <%s> is shared with class <%s>.' % (name, cls_name))
            return t

        cf: OrderedDict = self.logger_configs.get(name)
        if cf is None:
            self._L.debug('Create logger <%s> with default configuration.' % name)
            cf = self.logger_configs.get('default')
        level = cf.get('log_level')
        fmt = cf.get('format')
        _L = self._create_logger(name, level=level, fmt=fmt)
        self._L.debug('Create logger <%s> successful!' % name)
        out_file = cf.get('out_file')
        file_fmt = cf.get('format_file')
        if out_file is None:
            return _L
        if not isinstance(out_file, list):
            out_file = [out_file]
        for file in out_file:
            if file == 'self' or file == "":
                file = None
            is_new, file_name, fh = self._create_file(name, fmt=file_fmt, file_name=file)
            if is_new:
                self._L.debug('Create new log file: %s' % file_name)
            else:
                self._L.debug('Log file <%s> is shared with logger <%s>' % (file_name, name))
            if fh is not None:
                _L.addHandler(fh)
        return _L


GLogger = LoggerManager(LOGGER_CONFIG_FILE)

if GLogger.ALLOW_ABSTRACT:
    class LoggerMeta(type):
        def __new__(mcs, name: str, base: tuple, attrs: dict):
            full_name = attrs.get('logger_name')
            if full_name is None:
                full_name = attrs['__module__'] + '.' + attrs['__qualname__']
            attrs['_L'] = GLogger.get(full_name, attrs['__qualname__'])
            return super().__new__(mcs, name, base, attrs)
else:
    import abc


    class LoggerMeta(abc.ABCMeta):
        # def __init__(cls, name: str, base: tuple, attrs: dict):
        #     super().__init__(cls)
        #     print('I am init!{}'.format(cls.__name__))
        #
        # #
        # def __call__(cls, *args, **kwargs):
        #     super().__call__(*args, **kwargs)
        #     print('I am call!{}'.format(cls.__name__))

        def __new__(mcs, name: str, base: tuple, attrs: dict):
            for attr in attrs:
                x = attrs[attr]
                if hasattr(x, '__isabstractmethod__') and x.__isabstractmethod__:
                    GLogger._L.debug("%s has abstruct method %s, and we won't make logger for it." % (x, name))
                    return super().__new__(mcs, name, base, attrs)
            _name = attrs.get('_LOGGER_NAME')
            full_name = attrs['__module__'] + '.' + attrs['__qualname__']
            _name = full_name if _name is None else _name
            attrs['_L'] = GLogger.get(_name, full_name)
            return super().__new__(mcs, name, base, attrs)
