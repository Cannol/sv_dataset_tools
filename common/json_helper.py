import json
import numpy
import os
from collections import OrderedDict
if __name__ == '__main__':
    from common import GLogger
else:
    from .logger import GLogger
"""
this script is designed for transfer json to class config and create the object
"""

_L = GLogger.get('JsonHelper', 'common.json_helper')

DEFAULT_ASCII = True


def SaveToFile(full_path, dict_obj, create_dir=False, description=None, **kwargs):
    str_dict = json.dumps(dict_obj, **kwargs)
    dir_name = os.path.dirname(full_path)
    if create_dir and not os.path.exists(dir_name):
        os.makedirs(dir_name)
    with open(full_path, 'w') as f:
        f.write(str_dict)
    if description:
        _L.info(description)


def ReadFromFile(full_path, description=None, **kwargs):
    if not os.path.exists(full_path): return None
    with open(full_path) as f:
        dict_obj = json.load(f, **kwargs)
    if description:
        _L.info(description)
    return dict_obj


class JsonEncoderCls(json.JSONEncoder):
    """
    Using this JsonEncoder to encoder classes that inherited from JsonTransBase
    The Encoder will call the <object at JsonTransBase>.to_dict function automatically
    This encoder also support numpy
    """
    def default(self, o):
        if isinstance(o, JsonTransBase):
            return o.to_dict()
        elif isinstance(o, numpy.ndarray):
            return o.tolist()
        else:
            return super().default(o)


class JsonTransBase(object):

    def to_dict(self):
        """
        save the object to dict
        this function is the default json pre-transfer
        all the variables that name doesn't start with '_' will be writen to json-string automatically

        if you want to change the output dict, overriding it in your class
        :return: dict
        """
        d_out = {}
        for d in self.__dict__:
            if not d.startswith('_'):
                d_out[d] = self.__dict__[d]
        return d_out

    @property
    def Indent(self):
        if hasattr(self, '_indent_'):
            return self._indent_
        else:
            return None

    @Indent.setter
    def Indent(self, value):
        setattr(self, '_indent_', value)

    @property
    def Ascii(self):
        if hasattr(self, '_ensure_ascii_'):
            return self._ensure_ascii_
        else:
            return DEFAULT_ASCII

    @Ascii.setter
    def Ascii(self, value: bool):
        assert isinstance(value, bool), 'Bool value needed!'
        setattr(self, '_ensure_ascii_', value)

    @property
    def Json(self):
        d_out = self.to_dict()
        return json.dumps(d_out, cls=JsonEncoderCls, indent=self.Indent, ensure_ascii=self.Ascii)

    @Json.setter
    def Json(self, json_save_path):
        d_out = self.to_dict()
        with open(json_save_path, 'w') as f:
            json.dump(d_out, f, cls=JsonEncoderCls, indent=self.Indent, ensure_ascii=self.Ascii)

    def from_dict(self, obj_dict):
        """
        This function initialize the object by dict
        It is included: JsonTransBase, Numpy and OrderedDict parsing.
        :param obj_dict:
        :return:
        """
        for key in obj_dict:
            value = obj_dict[key]
            v_ = getattr(self, key, None)
            if v_ is not None:
                if isinstance(v_, JsonTransBase):
                    if isinstance(value, dict):
                        v_.from_dict(value)
                    else:
                        raise TypeError('JsonTransBase must use a dict to get object, but we got type: {}'.format(type(value)))
                elif isinstance(v_, numpy.ndarray):
                    if isinstance(value, list):
                        new_v = numpy.array(value)
                        if v_.dtype == new_v.dtype:
                            setattr(self, key, new_v)
                        else:
                            raise TypeError('Numpy type does not match! {} vs. {}'
                                            ', please check your class {} or json file'.format(v_.dtype, new_v.dtype, type(self)))
                    else:
                        raise TypeError('Numpy must be created by list, but we got type: {}'.format(type(value)))
                elif isinstance(v_, dict) and not isinstance(v_, OrderedDict) \
                        and isinstance(value, OrderedDict):
                    new_v = {}
                    for kk in value:
                        new_v[kk] = value[kk]
                    setattr(self, key, new_v)
                elif isinstance(v_, OrderedDict) and not isinstance(value, OrderedDict):
                    if isinstance(value, dict):
                        raise TypeError('You have to use OrderedDict to parse json!')
                    else:
                        raise TypeError('value of the key {} must be dict'.format(key))
                elif type(v_) == type(value):
                    setattr(self, key, value)
                else:
                    raise TypeError('Type does not match! {} vs. {}, please check your class {} or json file'.format(type(v_), type(value), type(self)))
            elif hasattr(self, key):
                _L.debug("Detecting <None Type> in this class <{}> for key <{}>, the value is given by json file.".format(type(self), key))
                setattr(self, key, value)
            else:
                _L.warn("The key <{}> doesn't exist in class <{}>, discarded.".format(key, type(self)))

    @classmethod
    def _GetObj(cls, o_dict):
        obj = cls()
        obj.from_dict(o_dict)
        return obj

    @classmethod
    def MakeNewFromJsonFile(cls, json_file, ordered_dict=False):
        with open(json_file) as f:
            if ordered_dict:
                o_dict = json.load(f, object_pairs_hook=OrderedDict)
            else:
                o_dict = json.load(f)
        return cls._GetObj(o_dict)

    @classmethod
    def MakeNewFromJson(cls, json_str, ordered_dict=False):
        if ordered_dict:
            o_dict = json.loads(json_str, object_pairs_hook=OrderedDict)
        else:
            o_dict = json.loads(json_str)
        return cls._GetObj(o_dict)

    def update_obj_from_json_file(self, json_file, ordered_dict=False):
        with open(json_file) as f:
            if ordered_dict:
                o_dict = json.load(f, object_pairs_hook=OrderedDict)
            else:
                o_dict = json.load(f)
        return self.from_dict(o_dict)

    def update_obj_from_json(self, json_str, ordered_dict=False):
        if ordered_dict:
            o_dict = json.loads(json_str, object_pairs_hook=OrderedDict)
        else:
            o_dict = json.load(json_str)
        return self.from_dict(o_dict)


if __name__ == '__main__':
    class A(JsonTransBase):
        def __init__(self):
            self.this = '123'
            self.that = '你好'
            self.where = 555
            self.bf = OrderedDict()
            self.bf['aaa'] = 100
            self.nn = numpy.ones((10,))

    class B(JsonTransBase):
        def __init__(self):
            self.aaaaaaa = '2'
            self.fff = 4

    class Use(JsonTransBase):
        def _play(self):
            pass

        def tt(self):
            pass

        def __init__(self):
            self.a = 100
            self.b = 'dfdf'
            self.c = 24.5
            self._d = 123
            self._e = '555'
            self.aa = A()

    d = Use()
    d.Indent = 4
    print(type(d.aa.bf))
    print(d.Json)
    d.Json = 'test.json'

    x = Use.MakeNewFromJsonFile('test.json', ordered_dict=True)
    print(x)
