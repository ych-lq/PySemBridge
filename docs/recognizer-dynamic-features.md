# Recognizer Dynamic Feature Coverage

This document summarizes the AST-level dynamic feature recognizers implemented
in `pysembridge/recognizer/features.py`.

The recognizer focuses on Python dynamic semantics with stable syntax hooks,
standard-library APIs, or data-model protocol names. These patterns map to
candidate semantic gaps that can later be compiled into Semantic Bridge IR and
validated by an analyzer backend.

## Fixed Dynamic Patterns

The current recognizer covers these feature groups:

- Dynamic receiver and attribute resolution:
  `getattr`, `setattr`, `hasattr`, `delattr`, instance `__getattr__`,
  instance `__getattribute__`, and module-level `__getattr__`.
- Descriptor and binding protocol:
  `__get__`, `__set__`, `__delete__`, `property`, `cached_property`, and dynamic
  method injection through attribute assignment.
- Callable objects and higher-order calls:
  `__call__`, `functools.partial`, callable arguments, `map`, `filter`,
  `reduce`, and `sorted`.
- Class creation and metaprogramming:
  multiple inheritance, `super`, metaclass declarations, `__mro_entries__`,
  `__init_subclass__`, `__set_name__`, `type(...)`, `types.new_class`, and
  `types.prepare_class`.
- Dynamic imports and plugin registration:
  `__import__`, `importlib.import_module`, framework registration calls, plugin
  registration calls, and `importlib.metadata.entry_points`-style entry-point
  discovery.
- Runtime rebinding:
  alias assignments, lambda rebinding, conditional binding, monkey patching,
  module `__class__` rebinding, and platform/OS guarded branches.
- String and container flow:
  dict/list/tuple literals, subscripts, comprehensions, generator expressions,
  f-strings, `%` formatting, `.format`, `.format_map`, string joins, string
  concatenation, and accumulator updates.
- Registered dispatch and callback tables:
  callback dictionaries, callback containers, `functools.singledispatch`,
  `.register`, and `.dispatch`.
- Dynamic code and serialization:
  `compile`, `eval`, `exec`, `json.loads`, `yaml.load`, `pickle.loads`,
  `pickle.load`, `__reduce__`, `__reduce_ex__`, and `__setstate__`.
- Context managers and iteration:
  `with`, `async with`, `__enter__`, `__exit__`, `__aenter__`, `__aexit__`,
  `for`, `async for`, `__iter__`, `__next__`, `yield`, and `yield from`.
- Async and concurrency scheduling:
  `async def`, `await`, `asyncio.create_task`, `asyncio.ensure_future`,
  `.add_done_callback`, `.cancel`, event-loop callback APIs, `Thread.start`,
  `Process.start`, executor `.submit`, and executor `.map`.
- Local context and typing boundaries:
  `threading.local`, `contextvars.ContextVar`, `contextvars.copy_context`,
  `typing.Any`, untyped/partially typed functions, `typing.Protocol`,
  `TypeGuard`, `TypeIs`, and `dataclass`/`dataclass_transform`.

## Feature Families

`pysembridge/recognizer/classifier.py` groups feature hits into semantic gap
families:

- `dynamic_receiver_callgraph`
- `container_dict_key_flow`
- `string_builder_flow`
- `rebinding_platform_flow`
- `dynamic_attribute_protocol`
- `dynamic_class_metaprogramming`
- `callback_parser_dispatch`
- `serialization_field_flow`
- `dynamic_code_execution`
- `typing_model_gap`

These families are intentionally broader than individual feature kinds. They
are used by the generic synthesizer to choose bridge hypotheses and evidence
templates.

## Regression Sample

The regression fixture lives at:

```text
tests/fixtures/recognizer_gaps/dynamic_gap_sample.py
```

It intentionally contains compact examples of fixed dynamic features such as
`getattr`, descriptor methods, metaclasses, `singledispatch`, `partial`, dynamic
type creation, context managers, iterators, threading, context variables,
typing guards, and string/container flows.

Run the recognizer regression test with:

```bash
python3 -m unittest tests.test_recognizer_features
```

Or run all tests:

```bash
python3 -m unittest discover -s tests
```

## Notes

The recognizer does not execute dynamic code. It only parses Python source into
AST nodes and records stable syntactic or protocol-level anchors. Potentially
dangerous names such as `eval`, `exec`, and `pickle.loads` are treated as
analysis targets, not as executable behavior inside PySemBridge.
