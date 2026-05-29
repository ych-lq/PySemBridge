"""AST feature extraction for Python dynamic semantic gap recognition."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FeatureHit:
    kind: str
    file: str
    line: int
    expr: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "file": self.file,
            "line": self.line,
            "expr": self.expr,
            "detail": self.detail,
        }


def extract_python_features(project_path: Path, max_files: int = 2000) -> list[FeatureHit]:
    project_path = project_path.resolve()
    hits: list[FeatureHit] = []
    for idx, path in enumerate(sorted(project_path.rglob("*.py"))):
        if idx >= max_files:
            break
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text)
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        relpath = str(path.relative_to(project_path))
        visitor = _FeatureVisitor(relpath, text)
        visitor.visit(tree)
        hits.extend(visitor.hits)
    return hits


class _FeatureVisitor(ast.NodeVisitor):
    def __init__(self, relpath: str, text: str) -> None:
        self.relpath = relpath
        self.text = text
        self.hits: list[FeatureHit] = []
        self.branch_depth = 0
        self.try_depth = 0
        self.function_stack: list[str] = []
        self.class_stack: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node.func)
        expr = ast.get_source_segment(self.text, node) or call_name

        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            self._add(
                "dynamic_receiver_call",
                node,
                expr,
                receiver=node.func.value.id,
                method=node.func.attr,
            )

        if _is_framework_registration_call(call_name):
            self._add("framework_registration", node, expr, callee=call_name)

        if _is_plugin_registration_call(call_name):
            self._add("plugin_registration", node, expr, callee=call_name)

        if _has_callable_argument(node):
            self._add("callback_argument", node, expr, callee=call_name)

        if call_name == "type" and len(node.args) >= 3:
            self._add("dynamic_type_construction", node, expr)

        if call_name in {"types.new_class", "types.prepare_class"} or call_name.endswith(
            (".new_class", ".prepare_class")
        ):
            self._add("dynamic_type_construction", node, expr, callee=call_name)

        if call_name in {"functools.partial", "functools.partialmethod"} or call_name.endswith(
            (".partial", ".partialmethod")
        ):
            self._add("partial_application", node, expr, callee=call_name)

        if call_name in {"getattr", "setattr", "hasattr", "delattr"}:
            self._add(
                "dynamic_attribute_access",
                node,
                expr,
                builtin=call_name,
                dynamic_name=_argument_is_dynamic(node, 1),
            )

        if call_name in {"__import__", "importlib.import_module"} or call_name.endswith(".import_module"):
            self._add("dynamic_import", node, expr, callee=call_name)

        if call_name in {"compile", "eval", "exec"}:
            self._add("dynamic_code_execution", node, expr, callee=call_name)

        if isinstance(node.func, ast.Attribute) and node.func.attr == "join":
            if node.args and isinstance(node.args[0], ast.GeneratorExp):
                self._add("string_join_generator", node, expr)
            else:
                self._add("string_join_builder", node, expr)

        if isinstance(node.func, ast.Attribute) and node.func.attr in {"format", "format_map"}:
            self._add("string_format_builder", node, expr, method=node.func.attr)

        if call_name in {"map", "filter", "reduce", "sorted"}:
            self._add("higher_order_function", node, expr, callee=call_name)

        if call_name.endswith((".register", ".dispatch")):
            self._add("registry_dispatch", node, expr, callee=call_name)

        if call_name in {"asyncio.create_task", "asyncio.ensure_future"} or call_name.endswith(
            (".create_task", ".ensure_future")
        ):
            self._add("async_task_schedule", node, expr, callee=call_name)

        if call_name.endswith((".add_done_callback", ".cancel")):
            self._add("async_task_callback", node, expr, callee=call_name)

        if call_name.endswith((".run_until_complete", ".call_soon", ".call_later", ".add_reader", ".add_writer")):
            self._add("event_loop_dispatch", node, expr, callee=call_name)

        if call_name.endswith((".start", ".submit")) and _looks_concurrency_receiver(call_name):
            self._add("concurrency_schedule", node, expr, callee=call_name)

        if _is_context_storage_call(call_name):
            self._add("context_local_storage", node, expr, callee=call_name)

        if call_name in {"json.loads", "yaml.load", "pickle.loads"} or call_name.endswith((".loads", ".load")):
            self._add("deserialization", node, expr, callee=call_name)

        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        expr = ast.get_source_segment(self.text, node) or "with"
        self._add("context_manager_use", node, expr, async_context=False)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        expr = ast.get_source_segment(self.text, node) or "async with"
        self._add("context_manager_use", node, expr, async_context=True)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        expr = ast.get_source_segment(self.text, node.iter) or "for"
        self._add("iterator_protocol_use", node, expr, async_iter=False)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        expr = ast.get_source_segment(self.text, node.iter) or "async for"
        self._add("iterator_protocol_use", node, expr, async_iter=True)
        self.generic_visit(node)

    def visit_Yield(self, node: ast.Yield) -> None:
        expr = ast.get_source_segment(self.text, node) or "yield"
        self._add("generator_protocol", node, expr)
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        expr = ast.get_source_segment(self.text, node) or "yield from"
        self._add("generator_protocol", node, expr, delegation=True)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        expr = ast.get_source_segment(self.text, node) or "subscript"
        self._add("container_subscript", node, expr, index=_slice_expr(self.text, node.slice))
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        expr = ast.get_source_segment(self.text, node) or "dict"
        self._add("dict_literal", node, expr)
        if any(_looks_callable(value) for value in node.values):
            self._add("callback_dict", node, expr)
        self.generic_visit(node)

    def visit_List(self, node: ast.List) -> None:
        expr = ast.get_source_segment(self.text, node) or "list"
        self._add("list_literal", node, expr, element_count=len(node.elts))
        if any(_looks_callable(item) for item in node.elts):
            self._add("callback_container", node, expr)
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        expr = ast.get_source_segment(self.text, node) or "tuple"
        self._add("tuple_literal", node, expr, element_count=len(node.elts))
        if any(_looks_callable(item) for item in node.elts):
            self._add("callback_container", node, expr)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        expr = ast.get_source_segment(self.text, node) or "list comprehension"
        self._add("comprehension_flow", node, expr, comprehension="list")
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        expr = ast.get_source_segment(self.text, node) or "set comprehension"
        self._add("comprehension_flow", node, expr, comprehension="set")
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        expr = ast.get_source_segment(self.text, node) or "dict comprehension"
        self._add("dict_comprehension_flow", node, expr)
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        expr = ast.get_source_segment(self.text, node) or "generator expression"
        self._add("generator_expression_flow", node, expr)
        self.generic_visit(node)

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:
        expr = ast.get_source_segment(self.text, node) or "f-string"
        self._add("f_string_builder", node, expr)
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        expr = ast.get_source_segment(self.text, node) or "binary operation"
        if isinstance(node.op, ast.Mod) and _string_like(node.left):
            self._add("percent_string_format_builder", node, expr)
        elif isinstance(node.op, ast.Add) and (_string_like(node.left) or _string_like(node.right)):
            self._add("string_concat_builder", node, expr)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        expr = ast.get_source_segment(self.text, node) or "assignment"
        if isinstance(node.value, ast.Lambda):
            self._add("function_rebinding", node, expr)
        if isinstance(node.value, (ast.Name, ast.Attribute)) and any(isinstance(t, ast.Name) for t in node.targets):
            self._add("alias_assignment", node, expr)
        if any(isinstance(t, ast.Attribute) for t in node.targets):
            self._add("monkey_patch_assignment", node, expr)
            if any(_is_module_class_assignment(t) for t in node.targets if isinstance(t, ast.Attribute)):
                self._add("module_class_rebinding", node, expr)
            if _looks_callable(node.value):
                self._add("dynamic_method_injection", node, expr)
        if self.branch_depth > 0 and _assignment_import_or_function_like(node):
            self._add("conditional_binding", node, expr)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        expr = ast.get_source_segment(self.text, node) or "augmented assignment"
        if isinstance(node.op, ast.Add):
            self._add("string_accumulator_builder", node, expr)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        expr = ast.get_source_segment(self.text, node.test) or "if"
        names = {_name.id for _name in ast.walk(node.test) if isinstance(_name, ast.Name)}
        if names.intersection({"sys", "os", "platform"}) or _contains_platform_attr(node.test):
            self._add("platform_branch", node, expr)
        self.branch_depth += 1
        self.generic_visit(node)
        self.branch_depth -= 1

    def visit_Import(self, node: ast.Import) -> None:
        expr = ast.get_source_segment(self.text, node) or "import"
        if self.branch_depth > 0 or self.try_depth > 0:
            self._add("conditional_import", node, expr)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        expr = ast.get_source_segment(self.text, node) or "from import"
        if self.branch_depth > 0 or self.try_depth > 0:
            self._add("conditional_import", node, expr, module=node.module or "")
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        self.try_depth += 1
        self.generic_visit(node)
        self.try_depth -= 1

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for deco in node.decorator_list:
            deco_expr = ast.get_source_segment(self.text, deco) or _call_name(deco)
            if _is_dataclass_decorator(deco_expr):
                self._add("dataclass_transform", node, f"@{deco_expr}", class_name=node.name)
            if _is_single_dispatch_decorator(deco_expr):
                self._add("single_dispatch_registration", node, f"@{deco_expr}", class_name=node.name)
        if len(node.bases) > 1:
            self._add("multiple_inheritance", node, f"class {node.name}", base_count=len(node.bases))
        for keyword in node.keywords:
            if keyword.arg == "metaclass":
                self._add(
                    "metaclass_declaration",
                    node,
                    f"class {node.name}",
                    metaclass=ast.get_source_segment(self.text, keyword.value) or _call_name(keyword.value),
                )
        if node.keywords or node.bases:
            for base in node.bases:
                base_name = _call_name(base)
                if base_name in {"type", "ABCMeta"} or base_name.endswith("Meta"):
                    self._add("metaclass_protocol", node, f"class {node.name}", base=base_name)
                if base_name in {"Protocol", "typing.Protocol"} or base_name.endswith(".Protocol"):
                    self._add("protocol_structural_typing", node, f"class {node.name}", base=base_name)
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name.startswith("__") and item.name.endswith("__"):
                self._add_protocol_method(item, node.name)
                self._add(
                    "special_method_protocol",
                    item,
                    f"class {node.name}.{item.name}",
                    class_name=node.name,
                    method=item.name,
                )
            if isinstance(item, ast.FunctionDef):
                for deco in item.decorator_list:
                    deco_name = _call_name(deco.func) if isinstance(deco, ast.Call) else _call_name(deco)
                    if deco_name in {"property", "cached_property"} or deco_name.endswith(".setter"):
                        self._add("descriptor_property", item, f"{node.name}.{item.name}", decorator=deco_name)
                    if deco_name.endswith("singledispatchmethod"):
                        self._add("single_dispatch_registration", item, f"@{deco_name}", function=item.name)
        self.class_stack.append(node.name)
        self.generic_visit(node)
        self.class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        if not self.class_stack and node.name == "__getattr__":
            self._add("module_getattr_hook", node, "def __getattr__", function=node.name)
        for deco in node.decorator_list:
            deco_expr = ast.get_source_segment(self.text, deco) or _call_name(deco)
            self._add("decorator_control_flow", node, f"@{deco_expr}", function=node.name)
            if _is_framework_decorator(deco_expr):
                self._add("framework_wrapper", node, f"@{deco_expr}", function=node.name)
            if _is_single_dispatch_decorator(deco_expr):
                self._add("single_dispatch_registration", node, f"@{deco_expr}", function=node.name)
            if deco_expr.endswith(".register"):
                self._add("registry_dispatch", node, f"@{deco_expr}", function=node.name)
        if _is_type_guard_annotation(node.returns):
            self._add("type_narrowing_guard", node, f"def {node.name}", function=node.name)
        if _function_has_gradual_type(node):
            self._add("gradual_typing_boundary", node, f"def {node.name}", function=node.name)
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                self._add("closure_callback", child, f"nested function {child.name}", parent=node.name)
        if _returns_function_or_class(node):
            self._add("factory_function", node, f"def {node.name}", function=node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self._add("async_function", node, f"async def {node.name}", function=node.name)
        for deco in node.decorator_list:
            deco_expr = ast.get_source_segment(self.text, deco) or _call_name(deco)
            self._add("decorator_control_flow", node, f"@{deco_expr}", function=node.name)
            if _is_framework_decorator(deco_expr):
                self._add("framework_wrapper", node, f"@{deco_expr}", function=node.name)
        self.generic_visit(node)
        self.function_stack.pop()

    def visit_Await(self, node: ast.Await) -> None:
        expr = ast.get_source_segment(self.text, node) or "await"
        self._add("await_expression", node, expr)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        expr = ast.get_source_segment(self.text, node) or "annotated assignment"
        annotation = ast.get_source_segment(self.text, node.annotation) or _call_name(node.annotation)
        if _annotation_contains(annotation, {"Any", "typing.Any"}):
            self._add("gradual_typing_boundary", node, expr, annotation=annotation)
        if _annotation_contains(annotation, {"Protocol", "typing.Protocol"}):
            self._add("protocol_structural_typing", node, expr, annotation=annotation)
        if _annotation_contains(annotation, {"ContextVar", "contextvars.ContextVar"}):
            self._add("context_local_storage", node, expr, annotation=annotation)
        self.generic_visit(node)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self._add("nonlocal_closure_state", node, f"nonlocal {', '.join(node.names)}", names=node.names)
        self.generic_visit(node)

    def _add_protocol_method(self, node: ast.FunctionDef, class_name: str) -> None:
        method = node.name
        expr = f"class {class_name}.{method}"
        if method == "__getattr__":
            self._add("getattr_hook", node, expr, class_name=class_name)
        elif method == "__getattribute__":
            self._add("getattribute_hook", node, expr, class_name=class_name)
        elif method in {"__get__", "__set__", "__delete__"}:
            self._add("descriptor_protocol", node, expr, class_name=class_name, method=method)
        elif method == "__call__":
            self._add("callable_object_protocol", node, expr, class_name=class_name)
        elif method in {"__mro_entries__", "__init_subclass__", "__set_name__"}:
            self._add("class_creation_hook", node, expr, class_name=class_name, hook=method)
        elif method in {"__prepare__", "__new__", "__init__"} and class_name.endswith("Meta"):
            self._add("metaclass_protocol", node, expr, class_name=class_name, method=method)
        elif method in {"__enter__", "__exit__", "__aenter__", "__aexit__"}:
            self._add("context_manager_protocol", node, expr, class_name=class_name, method=method)
        elif method in {"__iter__", "__next__"}:
            self._add("iterator_protocol", node, expr, class_name=class_name, method=method)
        elif method in {"__reduce__", "__reduce_ex__", "__setstate__"}:
            self._add("pickle_protocol", node, expr, class_name=class_name, method=method)

    def _add(self, kind: str, node: ast.AST, expr: str, **detail: Any) -> None:
        self.hits.append(
            FeatureHit(
                kind=kind,
                file=self.relpath,
                line=getattr(node, "lineno", 1),
                expr=expr,
                detail=detail,
            )
        )


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Subscript):
        return _call_name(node.value)
    return ""


def _is_framework_registration_call(call_name: str) -> bool:
    method = call_name.rsplit(".", 1)[-1]
    return method in {
        "route",
        "add_route",
        "add_url_rule",
        "middleware",
        "on_event",
        "add_event_handler",
        "register_blueprint",
        "include_router",
    }


def _is_framework_decorator(expr: str) -> bool:
    return any(token in expr for token in (".route", ".middleware", ".on_event", "router.", "app."))


def _is_plugin_registration_call(call_name: str) -> bool:
    method = call_name.rsplit(".", 1)[-1]
    return method in {
        "register",
        "unregister",
        "add_plugin",
        "load_plugin",
        "entry_points",
        "hookimpl",
        "connect",
        "signal",
    }


def _is_context_storage_call(call_name: str) -> bool:
    return call_name in {"threading.local", "contextvars.ContextVar", "contextvars.copy_context"} or call_name.endswith(
        (".local", ".ContextVar", ".copy_context")
    )


def _looks_concurrency_receiver(call_name: str) -> bool:
    if call_name.endswith((".submit", ".map")):
        return True
    if not call_name.endswith(".start"):
        return False
    receiver = call_name.rsplit(".", 1)[0].lower()
    return any(token in receiver for token in ("thread", "process", "pool", "executor", "task"))


def _is_module_class_assignment(node: ast.Attribute) -> bool:
    if node.attr != "__class__":
        return False
    return isinstance(node.value, (ast.Name, ast.Attribute))


def _is_single_dispatch_decorator(expr: str) -> bool:
    return expr in {"singledispatch", "functools.singledispatch", "singledispatchmethod"} or expr.endswith(
        (".singledispatch", ".singledispatchmethod")
    )


def _is_dataclass_decorator(expr: str) -> bool:
    return expr in {"dataclass", "dataclasses.dataclass", "dataclass_transform"} or expr.endswith(
        (".dataclass", ".dataclass_transform")
    )


def _is_type_guard_annotation(node: ast.AST | None) -> bool:
    annotation = _call_name(node) if node is not None else ""
    return annotation in {"TypeGuard", "typing.TypeGuard", "TypeIs", "typing.TypeIs"} or annotation.endswith(
        (".TypeGuard", ".TypeIs")
    )


def _function_has_gradual_type(node: ast.FunctionDef) -> bool:
    annotations: list[ast.AST] = []
    if node.returns is not None:
        annotations.append(node.returns)
    annotations.extend(arg.annotation for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs] if arg.annotation)
    if node.args.vararg and node.args.vararg.annotation:
        annotations.append(node.args.vararg.annotation)
    if node.args.kwarg and node.args.kwarg.annotation:
        annotations.append(node.args.kwarg.annotation)
    return any(_annotation_contains(_call_name(annotation), {"Any", "typing.Any"}) for annotation in annotations)


def _annotation_contains(annotation: str, names: set[str]) -> bool:
    parts = {part.strip("[] ,") for part in annotation.replace("|", ",").replace("[", ",").replace("]", ",").split(",")}
    return bool(parts.intersection(names) or annotation in names or any(annotation.endswith(f".{name}") for name in names))


def _has_callable_argument(node: ast.Call) -> bool:
    return any(_looks_callable(arg) for arg in [*node.args, *(kw.value for kw in node.keywords)])


def _looks_callable(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return True
    if isinstance(node, ast.Name):
        return True
    if isinstance(node, ast.Attribute):
        return True
    return False


def _argument_is_dynamic(node: ast.Call, index: int) -> bool:
    if len(node.args) <= index:
        return False
    arg = node.args[index]
    return not isinstance(arg, ast.Constant)


def _slice_expr(text: str, node: ast.AST) -> str:
    if isinstance(node, ast.Index):  # Python 3.8 compatibility
        node = node.value
    return ast.get_source_segment(text, node) or "?"


def _string_like(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.JoinedStr):
        return True
    return False


def _contains_platform_attr(node: ast.AST) -> bool:
    names = {_call_name(child) for child in ast.walk(node)}
    return any(
        name.startswith(("sys.", "os.", "platform.")) or name in {"sys", "os", "platform"} for name in names
    )


def _assignment_import_or_function_like(node: ast.Assign) -> bool:
    return isinstance(node.value, (ast.Name, ast.Attribute, ast.Call, ast.Lambda))


def _returns_function_or_class(node: ast.FunctionDef) -> bool:
    nested_names = {child.name for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    for child in ast.walk(node):
        if isinstance(child, ast.Return):
            if isinstance(child.value, ast.Name) and child.value.id in nested_names:
                return True
            if isinstance(child.value, ast.Lambda):
                return True
            if isinstance(child.value, ast.Call) and _call_name(child.value.func) == "type":
                return True
    return False
