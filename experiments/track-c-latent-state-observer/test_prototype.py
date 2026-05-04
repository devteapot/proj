import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from prototype import CounterProbeDecoder, LatentCounterRuntime, OpaqueLatentState, SlopObserver


class LatentStateObserverTests(unittest.TestCase):
    def setUp(self):
        self.decoder = CounterProbeDecoder()
        self.observer = SlopObserver(self.decoder)

    def decoded_value(self, runtime):
        tree = self.observer.project(runtime)
        return tree["children"][0]["properties"]["decoded_state"]["value"]

    def test_state_can_be_snapshotted_and_restored(self):
        runtime = LatentCounterRuntime()
        runtime.apply("increment")
        snapshot = runtime.snapshot()
        expected = self.decoded_value(runtime)

        runtime.apply("increment")
        self.assertNotEqual(expected, self.decoded_value(runtime))

        runtime.restore(snapshot)
        self.assertEqual(expected, self.decoded_value(runtime))

    def test_perturbing_latent_changes_decoded_observer_output(self):
        runtime = LatentCounterRuntime()
        before = self.observer.project(runtime)

        runtime.perturb(index=0, amount=17)
        after = self.observer.project(runtime)

        before_state = before["children"][0]["properties"]["decoded_state"]
        after_state = after["children"][0]["properties"]["decoded_state"]
        self.assertNotEqual(before_state, after_state)

    def test_observer_marks_decoded_state_as_diagnostic_not_authoritative(self):
        runtime = LatentCounterRuntime()
        runtime.apply("increment")
        tree = self.observer.project(runtime)
        probe_node = tree["children"][0]

        self.assertEqual("diagnostic_projection", tree["properties"]["authority"])
        self.assertFalse(tree["properties"]["strong_projection_evidence"])
        self.assertTrue(probe_node["properties"]["probed"])
        self.assertFalse(probe_node["properties"]["authoritative"])
        self.assertTrue(probe_node["meta"]["diagnostic"])
        self.assertIn("Mock latent only", tree["meta"]["caveat"])

    def test_runtime_api_has_no_symbolic_app_source_of_truth(self):
        runtime = LatentCounterRuntime()
        public_names = {
            name
            for name, value in inspect.getmembers(runtime)
            if not name.startswith("_") and not inspect.ismethoddescriptor(value)
        }

        self.assertIn("apply", public_names)
        self.assertIn("snapshot", public_names)
        self.assertIn("restore", public_names)
        self.assertIn("perturb", public_names)
        self.assertIn("probe", public_names)
        self.assertNotIn("counter", public_names)
        self.assertNotIn("counter_value", public_names)
        self.assertNotIn("todos", public_names)
        self.assertNotIn("state", public_names)

        self.assertFalse(hasattr(runtime, "counter_value"))
        self.assertFalse(hasattr(runtime, "state"))

    def test_opaque_latent_does_not_expose_symbolic_fields(self):
        latent = OpaqueLatentState.from_bytes([1, 2, 3, 4])

        self.assertEqual(bytes([1, 2, 3, 4]), latent.to_bytes())
        self.assertFalse(hasattr(latent, "counter"))
        self.assertFalse(hasattr(latent, "counter_value"))
        self.assertFalse(hasattr(latent, "todos"))


if __name__ == "__main__":
    unittest.main()
