from pathlib import Path
import unittest

from pysembridge.recognizer.features import extract_python_features


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "recognizer_gaps"


class RecognizerFeatureExtractionTest(unittest.TestCase):
    def test_extracts_dynamic_gap_features_from_small_sample(self) -> None:
        hits = extract_python_features(FIXTURE_DIR)
        by_kind = {}
        for hit in hits:
            by_kind.setdefault(hit.kind, []).append(hit)

        expected_kinds = {
            "dynamic_attribute_access",
            "dict_literal",
            "callback_dict",
            "container_subscript",
            "percent_string_format_builder",
            "string_format_builder",
            "f_string_builder",
            "higher_order_function",
            "callback_argument",
            "getattr_hook",
            "getattribute_hook",
            "descriptor_protocol",
            "callable_object_protocol",
            "class_creation_hook",
            "metaclass_declaration",
            "multiple_inheritance",
            "module_getattr_hook",
            "partial_application",
            "dynamic_type_construction",
            "dynamic_code_execution",
            "single_dispatch_registration",
            "registry_dispatch",
            "context_manager_protocol",
            "context_manager_use",
            "iterator_protocol",
            "iterator_protocol_use",
            "generator_protocol",
            "pickle_protocol",
            "dataclass_transform",
            "protocol_structural_typing",
            "type_narrowing_guard",
            "gradual_typing_boundary",
            "concurrency_schedule",
            "context_local_storage",
            "async_task_schedule",
            "async_task_callback",
        }

        self.assertTrue(
            expected_kinds.issubset(by_kind),
            f"missing feature kinds: {sorted(expected_kinds.difference(by_kind))}",
        )

        self.assertTrue(
            any(hit.expr == "getattr(handler, handler_name)" for hit in by_kind["dynamic_attribute_access"])
        )
        self.assertTrue(any(hit.expr == 'callbacks["audit"]' for hit in by_kind["container_subscript"]))
        self.assertTrue(any(hit.expr == '"payload=%s" % payload' for hit in by_kind["percent_string_format_builder"]))
        self.assertTrue(any(hit.expr == '"payload {}".format(payload)' for hit in by_kind["string_format_builder"]))
        self.assertTrue(any(hit.expr == "f\"{message}:{second_result}\"" for hit in by_kind["f_string_builder"]))
        self.assertTrue(any(hit.expr == "map(audit, [payload])" for hit in by_kind["higher_order_function"]))
        self.assertTrue(any(hit.expr == "class Handler.__getattr__" for hit in by_kind["getattr_hook"]))
        self.assertTrue(any(hit.expr == "class Descriptor.__get__" for hit in by_kind["descriptor_protocol"]))
        self.assertTrue(any(hit.expr == "class Derived" for hit in by_kind["multiple_inheritance"]))
        self.assertTrue(any(hit.expr == "functools.partial(audit, payload)" for hit in by_kind["partial_application"]))
        self.assertTrue(any(hit.expr == 'type("DynamicType", (), {})' for hit in by_kind["dynamic_type_construction"]))
        self.assertTrue(any(hit.expr == 'compile("payload", "<dynamic>", "eval")' for hit in by_kind["dynamic_code_execution"]))
        self.assertTrue(any(hit.expr == "@functools.singledispatch" for hit in by_kind["single_dispatch_registration"]))
        self.assertTrue(any(hit.expr == "with Managed() as managed:\n        managed.field = payload" for hit in by_kind["context_manager_use"]))
        self.assertTrue(any(hit.expr == "thread.start()" for hit in by_kind["concurrency_schedule"]))
        self.assertTrue(any(hit.expr == 'contextvars.ContextVar("payload")' for hit in by_kind["context_local_storage"]))


if __name__ == "__main__":
    unittest.main()
