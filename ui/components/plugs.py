import tkinter as tkk
from logging import Logger
from common.logger import LoggerMeta


# mouse events
MOUSE_LEFT = "<Button-1>"
MOUSE_RIGHT = "<Button-3>"
MOUSE_MID = "<Button-2>"
MOUSE_LEFT_RELEASE = "<ButtonRelease-1>"
MOUSE_RIGHT_RELEASE = "<ButtonRelease-3>"
MOUSE_MID_RELEASE = "<ButtonRelease-2>"
MOUSE_MOVE = "<Motion>"
ENTER = "<Enter>"
LEAVE = "<Leave>"

# widget focus events
FOCUS_IN = "<FocusIn>"
FOCUS_OUT = "<FocusOut>"

# widget state events
CONFIGURE_CHANGE = "<Configure>"
ACTIVE = "<Active>"
DEACTIVATE = "<Deactivate>"
EXPOSE = "<Expose>"

# special keys
# Keys = object()
# Keys.Ctrl = "Ctrl"
# Keys.

# key board event
def KeyPress(char=None): return "<KeyPress-%s>" % char if char else "<KeyPress>"

def KeyRelease(char=None): return "<KeyRelease-%s>" % char if char else "<KeyRelease>"


class WidgetClassHolder(metaclass=LoggerMeta):
    """
    对某个Widget对象批量管理事件
    """
    _L: Logger = None

    def __init__(self, widget: tkk.Widget, holder_name=None):
        if not holder_name:
            holder_name = type(self).__name__
        self._name = holder_name
        self._tag_cls_name = "%s-%s" % (widget.widgetName, holder_name)    # create a name to hold events
        self._widget = widget
        # self._root_master = widget
        self._is_enable = False
        self._initialize_all()

    def _initialize_all(self):
        self._L.error('You must implement this function to initialize all the event functions')
        raise NotImplementedError

    # @staticmethod
    # def get_root(master):
    #     root = master
    #     while root.parent:
    #         root = root.parent
    #     return root

    def _bind_event(self, event_sequence, func):
        self._widget.bind_class(self._tag_cls_name, event_sequence, func)

    def _bind_event_combination(self, event_list: list, func):
        events: str = ''.join(event_list)
        events.replace('><', '-')
        self._bind_event(events, func)

    @property
    def Enable(self):
        return self._is_enable

    @Enable.setter
    def Enable(self, value):
        if value == self._is_enable:
            return
        if value:
            self._register()
            self._is_enable = True
        else:
            self._unregister()
            self._is_enable = False

    def _register(self):
        t = list(self._widget.bindtags())
        try:
            i = t.index(self._tag_cls_name)
            if i > 0:
                t.pop(i)
                t.insert(0, self._tag_cls_name)
                self._widget.bindtags(tuple(t))
                self._L.warning("Widget [%s] Detect wrong order of banded tag, "
                                "don't modify widget's tags outside on your own!" % self._widget.widgetName)
            self._L.debug('The tag "%s" is already in widget "%s" tag list.' % (self._tag_cls_name,
                                                                                self._widget.widgetName))

        except ValueError:
            t.insert(0, self._tag_cls_name)
            self._widget.bindtags(tuple(t))
            self._L.debug('Bind "%s" to widget "%s" successful.' % (self._tag_cls_name, self._widget.widgetName))

    def _unregister(self):
        t = list(self._widget.bindtags())
        try:
            i = t.index(self._tag_cls_name)
            t.pop(i)
            self._widget.bindtags(tuple(t))
            self._L.debug('The tag "%s" is removed from widget "%s" tag list.' % (self._tag_cls_name,
                                                                                  self._widget.widgetName))
        except ValueError:
            self._L.debug('The tag "%s" is not in widget "%s" tag list' % (self._tag_cls_name,
                                                                           self._widget.widgetName))


class TagHolder(metaclass=LoggerMeta):
    """
    提供对类管理标签的功能
    """
    _L: Logger = None
    _tag_dict = {}
    # _tag_class_dict = {}

    def __init__(self):
        self._bind_master = []           # different high-level master (the root TK) handle will be saved here
        self._name = ""                  # class name
        self._event_func_dict = dict()   # event to function
        self._widgets = set()            # registered widgets

    @property
    def Name(self):
        return self._name

    # does the object of TagHolder been registered in _tag_dict?
    @property
    def IsRegistered(self):
        return True if self._tag_dict.get(self._name) else False

    @property
    def Events(self):
        return list(self._event_func_dict)

    @property
    def IsEmpty(self):
        if len(self._event_func_dict) <= 0:
            return True
        return False

    def __len__(self):
        return len(self._event_func_dict)

    def add_master(self, bind_master):
        master = bind_master
        while master.master:
            master = master.master
        if master in self._bind_master:
            self._L.debug("You have add a master with same root TK object.")
        else:
            self._bind_master.append(master)
            self._L.debug("Add new root TK object to bind_master, now we have {} in holder '{}'"
                          .format(len(self._bind_master), self._name))
            self._bind_new_master(master)

    def remove_master(self, bind_master):
        master = bind_master
        while master.master:
            master = master.master
        if master in self._bind_master:
            self._unbind_master(master)
            self._bind_master.remove(master)
            self._L.debug("Remove root TK object from bind_master, now we have {} in holder '{}'"
                          .format(len(self._bind_master), self._name))
        else:
            self._L.error("Tk object {} doesn't exist in holder list.".format(master))

    def _bind_new_master(self, master):
        for event in self._event_func_dict:
            master.bind_class(self._name, event, self._event_func_dict[event])

    def _unbind_master(self, master):
        for event in self._event_func_dict:
            master.unbind_class(self._name, event)

    def bind(self, event, func_a=None):
        if func_a is None:
            func_a = self.run_event
        func = self._event_func_dict.get(event)
        if func is None:
            for master in self._bind_master:
                master.bind_class(self._name, event, func_a)
            self._event_func_dict[event] = func_a
        elif func_a == func:
            raise ReferenceError("The combination of '{}' and '{}' is exists.".format(event, func_a))
        else:
            # change func
            for master in self._bind_master:
                master.bind_class(self._name, event, func_a)
            self._event_func_dict[event] = func_a

    def unbind(self, event, func_d=None):
        """
        unbind all of the banded master with one event
        func_d is not necessary unless you want to validate the combination of (event, func_d)
        :param event: right name sequence of event
        :param func_d: this function must match with the event in binding operation
        :return: not reference error
        """
        func = self._event_func_dict[event]
        if func is None:
            raise ReferenceError("The event of '{}' is not exists.".format(event))
        elif func_d == func or func_d is None:
            for master in self._bind_master:
                master.unbind_class(self._name, event)
        else:
            raise ReferenceError("The combination of '{}' and '{}' is not exists.".format(event, func_d))

    def register(self, widget):
        t = set(widget.bindtags()) | {self._name}
        widget.bindtags(tuple(t))
        self._widgets.add(widget)

    def unregister(self, widget):
        t = set(widget.bindtags()) - {self._name}
        widget.bindtags(tuple(t))
        self._widgets.discard(widget)

    def unregister_all(self):
        for widget in self._widgets:
            self.unregister(widget)
        self._widgets.clear()

    def unbind_all(self):
        for event in self._event_func_dict:
            self.unbind(event)
        self._event_func_dict.clear()

    def __del__(self):
        self.clear()
        del self._event_func_dict
        del self._widgets

    def clear(self):
        self.unregister_all()
        self.unbind_all()
        self._widgets.clear()

    # this function is inner function, if the group is create by another func, this one cannot be reach
    def run_event(self, event): raise NotImplementedError

    @classmethod
    def GetFullName(cls, group_name):
        return "%s-%s" % (cls.__name__, group_name)

    # return an empty holder object
    @classmethod
    def CreateEmpty(cls, group_name="default", exist_override=False):
        name = cls.GetFullName(group_name)
        holder = cls._tag_dict.get(name)
        if holder is None:
            holder = cls()
            holder._name = name
            cls._tag_dict[name] = holder
        else:
            if exist_override:
                holder.clear()
            else:
                raise Exception('The group name already exist! {}'.format(name))
        return holder

    @classmethod
    def Create(cls, bind_master, group_name="default"):
        name = cls.GetFullName(group_name)
        holder = cls._tag_dict.get(name)
        if holder is None:
            holder = cls()
            holder._name = name
            holder.add_master(bind_master)
            cls._tag_dict[name] = holder
        else:
            holder.add_master(bind_master)
        return holder

    @classmethod
    def Get(cls, group_name="default", raise_error=False):
        name = cls.GetFullName(group_name)
        holder = cls._tag_dict.get(name)
        if holder:
            return holder
        if raise_error:
            raise ReferenceError('Unknown group name: {} \n --> We have: {}'
                                 .format(group_name, [i for i in cls._tag_dict if i.startwith(cls.__name__)]))
        else:
            return None

    @classmethod
    def RemoveMaster(cls, bind_master, group_name="default"):
        holder = cls.Get(group_name, raise_error=True)
        holder.remove_master(bind_master)
        return holder

    @classmethod
    def Delete(cls, group_name="default"):
        holder: cls = cls.Get(group_name, raise_error=True)
        cls._tag_dict.pop(holder.Name)
        del holder

    @classmethod
    def CreateEvent(cls, bind_event, group_name="default", func=None):
        holder: cls = cls.Get(group_name)
        if func is not None:
            holder._func = func
        try:
            holder.bind(bind_event, func)
        except ReferenceError:
            cls._L.warning('You are trying to add the same event to one holder.[%s]' % bind_event)
        return holder

    @classmethod
    def RemoveEvent(cls, event_to_cancel, group_name="default"):
        holder = cls.Get(group_name, raise_error=True)
        holder.unbind(event_to_cancel)

    @classmethod
    def RemoveAllEvent(cls, group_name="default"):
        holder = cls.Get(group_name, raise_error=True)
        holder.unbind_all()

    @classmethod
    def RegisterWidget(cls, widget, group_name="default"):
        holder: cls = cls.Get(group_name, raise_error=True)
        holder.register(widget)

    @classmethod
    def UnregisterWidget(cls, widget, group_name="default"):
        holder: cls = cls.Get(group_name, raise_error=True)
        holder.unregister(widget)

    @classmethod
    def RegisterWidgets(cls, widgets, group_name="default"):
        holder: cls = cls.Get(group_name, raise_error=True)
        for widget in widgets:
            holder.register(widget)

    @classmethod
    def UnregisterWidgets(cls, widgets, group_name="default"):
        holder: cls = cls.Get(group_name, raise_error=True)
        for widget in widgets:
            holder.unregister(widget)


class _Tags(TagHolder):
    """
    This class used for create an unique Name Space for one class by its name
    """
    @classmethod
    def GetFullName(cls, group_name):
        return group_name

    def run_event(self, event): pass


# we have to register all the system widget to avoid mistaking use
__SystemTargetList = ['Checkbutton', 'Canvas', 'Entry',
                      'Frame', 'Label', 'LabelFrame', 'Listbox',
                      'Menu', 'Menubutton', 'Message', 'OptionMenu',
                      'PanedWindow', 'Radiobutton', 'Scale', 'Scrollbar',
                      'Spinbox', 'Text', 'Combobox', 'Notebook', 'Progressbar',
                      'Separator', 'Sizegrip', 'Treeview']

for target in __SystemTargetList:
    _Tags.CreateEmpty(target)


# A meta-class for creating class-name tag automatically
class TagMeta(type):
    _Holder: _Tags = None

    def __init__(cls, name: str, base: tuple, attrs: dict):
        has_widget = False
        for b in base:
            if issubclass(b, tkk.Widget):
                has_widget = True
                break
        assert has_widget, \
            "Class: {} must have at least one base class which inherits from Widget class or its subclass.".format(name)
        super().__init__(name, base, attrs)
        try:
            cls._Holder = _Tags.CreateEmpty(name)
        except Exception as e:
            # 1. class name must not be same as the widget name in Tkinter Package
            # 2. the class names in two in different files are same, which is not allowed
            assert True, str(e)

    # when generate a new instance, we register it into the event class
    def __call__(cls, *args, **kwargs):
        instance = super().__call__(*args, **kwargs)
        cls._Holder.add_master(instance)
        _Tags.RegisterWidget(instance, cls.__name__)
        return instance


class TagClassMeta(type):
    _Holder: _Tags = None

    def __init__(cls, name: str, base: tuple, attrs: dict):
        has_widget = False
        for b in base:
            if issubclass(b, tkk.Widget):
                has_widget = True
                break
        assert has_widget, \
            "Class: {} must have at least one base class which inherits from Widget class or its subclass.".format(name)
        super().__init__(name, base, attrs)
        try:
            cls._Holder = _Tags.CreateEmpty(name)
        except Exception as e:
            # 1. class name must not be same as the widget name in Tkinter Package
            # 2. the class names in two in different files are same, which is not allowed
            assert True, str(e)


# construct order: TagLogMeta --> LoggerMeta --> TagMeta
class TagLogMeta(LoggerMeta, TagMeta): ...


class MemoryValidateTag(TagHolder):
    """
    设置恢复操作，恢复到最后一次正确的值，同一组的widget共享同一个value_backup
    This Tag is designed only for Entry and Text
    """
    __FocusIn = tkk.EventType.FocusIn
    __FocusOut = tkk.EventType.FocusOut

    FocusInClean = 0
    FocusInSelectAll = 1

    class ValidateValueError(ValueError):
        def __init__(self, reason=""):
            self.reason = reason

        def __str__(self):
            return self.reason

    def __init__(self):
        super().__init__()
        self._value = ""
        self._validate_funcs = dict()

    def _set_property(self, allow_empty=False, clear_selection=True, strip_empty=True):
        self._reject_empty = not allow_empty
        self._clear_selection = clear_selection
        self._strip = strip_empty

    def _get_widget_value(self, widget):
        _value = ""
        if isinstance(widget, tkk.Entry):
            _value = widget.get()
        elif isinstance(widget, tkk.Text):
            _value = widget.get(0, tkk.END)
        if self._strip:
            return _value.strip()
        return _value

    def _focus_in(self, widget):
        self._value = self._get_widget_value(widget)
        self._L.debug("[{}] Remember value '{}'.".format(self._name, self._value))
        if hasattr(widget, 'mem_focus_in_option_tag'):
            op = widget.mem_focus_in_option
            if op == self.FocusInClean:
                widget.delete(0, tkk.END)
            elif op == self.FocusInSelectAll:
                widget.select_range(0, tkk.END)

    # 利用抛出异常的方法告诉Holder怎么做（使用此方法可以省略赋值过程）
    def _focus_out_exception(self, widget):
        if self._clear_selection:
            widget.select_clear()
        value_ = self._get_widget_value(widget)
        if value_ == self._value:
            self._L.debug('Nothing changed!')
            self._value = ""
            return
        try:
            if value_ == "" and self._reject_empty:
                raise self.ValidateValueError('Empty Value is not allowed.')
            value = self._validate_funcs[widget](value_)
            if value is None:
                # validate function return Nothing, so don't change value here
                return
            elif value != value_:
                self._L.debug(r'Value has been changed by validate function.')
            else:
                self._L.debug(r'Validate Pass!')
                return
        except self.ValidateValueError as error:
            value = self._value
            if str(error):
                self._L.error(error)
            else:
                self._L.error(r'Invalid value "{}" that cannot transfer to right format, recover to "{}"'
                              .format(value_, value))
        except ValueError as error:
            value = self._value
            self._L.error(r'ValueError "{}", recover to "{}"'.format(error, value))
        if isinstance(widget, tkk.Entry):
            widget.delete(0, tkk.END)
            widget.insert(tkk.END, value)
        elif isinstance(widget, tkk.Text):
            widget.delete(tkk.END, value)
            widget.insert(tkk.END, value)
        self._value = ""

    # # 不利用异常，需要返回一个是否恢复的flag
    # def _focus_out(self, widget):
    #     value = self._get_widget_value(widget)
    #     if self._validate_funcs[widget](value):
    #         self._L.debug('Validate pass! {}'.format(value))
    #         self._value = ""
    #         return
    #     if self._value is not None:
    #         if isinstance(widget, tkk.Entry):
    #             widget.delete(0, tkk.END)
    #             widget.insert(tkk.END, self._value)
    #         elif isinstance(widget, tkk.Text):
    #             widget.delete(tkk.END, self._value)
    #             widget.insert(tkk.END, self._value)
    #         self._L.debug('Recover value to: {}'.format(self._value))
    #         self._value = ""
    #     else:
    #         self._L.warning('Nothing be recovered, please check your code.')

    def run_event(self, event):
        if event.type == self.__FocusIn:
            self._focus_in(event.widget)
        elif event.type == self.__FocusOut:
            self._focus_out_exception(event.widget)
        else:
            self._L.error('Widget "{}" got unexpected event "{}"'.format(event.widget, event.type))

    def register_with_func(self, widget, func, focus_in_option=None):
        assert isinstance(widget, (tkk.Entry, tkk.Text)), \
            "Widget must in Entry or Text type! We got {}".format(type(widget))
        super().register(widget)
        self._validate_funcs[widget] = func
        if focus_in_option is not None:
            setattr(widget, 'mem_focus_in_option_tag', focus_in_option)

    def unregister(self, widget):
        super().unregister(widget)
        if self._validate_funcs.get(widget):
            self._validate_funcs.pop(widget)

    def clear(self):
        self._validate_funcs.clear()
        super().clear()

    @classmethod
    def Create(cls, bind_master, group_name="default", allow_empty=False, clear_selection=True, strip_empty=True):
        holder: cls = super().Create(bind_master, group_name)
        holder.bind("<FocusIn>")
        holder.bind("<FocusOut>")
        # holder.bind("<Return>", holder._widgets.)
        holder._set_property(allow_empty, clear_selection)
        return holder

    @classmethod
    def RegisterWidgetFuncs(cls, widget, validate_funcs, group_name="default", focus_in_option=None):
        holder: cls = cls.Get(group_name, raise_error=True)
        holder.register_with_func(widget, validate_funcs, focus_in_option)

    # ==== these functions we don't use in this class ====
    def register(self, widget): pass

    @classmethod
    def RegisterWidget(cls, widget, group_name="default"):
        assert True, "This method has been cancelled, please use RegisterWidgetFuncs instead"
