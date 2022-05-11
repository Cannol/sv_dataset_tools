import typing
import yaml
import os

if __name__ == '__main__':
    from common import GLogger
else:
    from .logger import GLogger

_L = GLogger.get('YamlHelper', 'common.yaml_helper')


class YamlConfigClassBase(object):
    __SAVE_FILE__ = ""

    @classmethod
    def SetFile(cls, file):
        cls.__SAVE_FILE__ = file

    @classmethod
    def Load(cls, file=None):
        if file is None:
            file = cls.__SAVE_FILE__
        else:
            cls.__SAVE_FILE__ = file
            if not os.path.exists(file):
                # use default and save to file
                cls.Save()
                _L.info('Create new config file for <%s> to: %s' % (cls.__name__, file))
                return
        with open(file, encoding="utf-8") as f:
            content = yaml.safe_load(f)
        for key in content:
            if hasattr(cls, key):
                setattr(cls, key, content[key])
            else:
                _L.warning('Skip an unknown key: {}'.format(key))
        _L.info('Load config <%s> from file: %s' % (cls.__name__, file))

    @classmethod
    def Save(cls, file=None):
        if file is None:
            file = cls.__SAVE_FILE__
        content = {key: cls.__dict__[key] for key in cls.__dict__ if (not key.startswith('_'))}
        with open(file, 'w', encoding="utf-8") as f:
            yaml.safe_dump(content, f)


