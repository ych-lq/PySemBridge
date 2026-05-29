import asyncio
import contextvars
import functools
import threading
import types
import typing
from dataclasses import dataclass


def __getattr__(name):
    return name.upper()


class DynamicMeta(type):
    def __prepare__(name, bases):
        return {}


class Handler:
    def __getattr__(self, name):
        return lambda value: value

    def __getattribute__(self, name):
        return object.__getattribute__(self, name)

    def __call__(self, value):
        return value

    def save(self, value):
        return "saved:%s" % value


class Descriptor:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        return instance

    def __set__(self, instance, value):
        instance.value = value


class Managed:
    field = Descriptor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class IterableBox:
    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration


class BaseA:
    def save(self, value):
        return value


class BaseB:
    pass


class Derived(BaseA, BaseB, metaclass=DynamicMeta):
    def save(self, value):
        return super().save(value)


class SubclassRegistry:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)


class Registered(SubclassRegistry):
    pass


class PickleShape:
    def __reduce__(self):
        return (dict, ())


@dataclass
class GeneratedRecord:
    name: str


class ShapeProtocol(typing.Protocol):
    def area(self) -> typing.Any:
        ...


def guard(value: typing.Any) -> typing.TypeGuard[str]:
    return isinstance(value, str)


@functools.singledispatch
def audit(value):
    return f"audit:{value}"


@audit.register
def _(value: int):
    return str(value)


def generated_numbers(values):
    yield from values


def run_dynamic_gap_sample(handler_name, payload):
    handler = Handler()
    method = getattr(handler, handler_name)
    first_result = method(payload)

    callbacks = {
        "audit": audit,
        "inline": lambda item: "inline {}".format(item),
    }
    selected = callbacks["audit"]
    second_result = selected(first_result)

    query = "payload=%s" % payload
    message = "payload {}".format(payload)
    summary = f"{message}:{second_result}"

    partial_audit = functools.partial(audit, payload)
    partial_audit()
    DynamicType = type("DynamicType", (), {})
    OtherDynamicType = types.new_class("OtherDynamicType")
    code = compile("payload", "<dynamic>", "eval")
    eval(code)
    with Managed() as managed:
        managed.field = payload
    for item in IterableBox():
        audit(item)
    thread = threading.Thread(target=audit, args=(payload,))
    thread.start()
    context_value = contextvars.ContextVar("payload")
    asyncio.create_task(audit(payload)).add_done_callback(audit)
    list(map(audit, [payload]))
    return query, message, summary, DynamicType, OtherDynamicType, context_value
