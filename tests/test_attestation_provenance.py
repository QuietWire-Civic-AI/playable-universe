import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "server" / "attestation_intake.py"

spec = importlib.util.spec_from_file_location("attestation_intake", MODULE_PATH)
intake = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(intake)


def packet():
    return {
        "schema": "playable.mobile-attestation.v0",
        "client_id": "browser:test-client",
        "created_at": "2026-10-06T23:45:00Z",
        "claim": {
            "text": "The test coffee cup is blue.",
            "kind": "witness_statement",
        },
        "witness": {
            "mode": "self_asserted_name",
            "display_name": "Test Witness",
            "identity_ref": None,
        },
        "assurance": {
            "class": "browser-self-asserted",
            "signature": None,
        },
        "evidence": [],
        "location": {
            "mode": "none",
            "latitude": None,
            "longitude": None,
            "accuracy_m": None,
            "place_label": None,
        },
        "sharing": {
            "candidate_visibility": "receipt-only",
            "media_disposition": "hash-only-v0",
        },
        "refs": [],
        "notes": [],
    }


class ProvenanceValidationTests(unittest.TestCase):
    def test_legacy_packet_gets_explicit_unspecified_provenance(self):
        cleaned = intake.validate_packet(packet())
        self.assertEqual(cleaned["provenance"], {
            "mode": "unspecified",
            "source_refs": [],
            "note": None,
        })

    def test_direct_observation_with_source_reference_is_preserved(self):
        value = packet()
        value["provenance"] = {
            "mode": "direct_observation",
            "source_refs": ["attest:source-example"],
            "note": "I am looking at it now.",
        }
        cleaned = intake.validate_packet(value)
        self.assertEqual(
            cleaned["provenance"]["mode"],
            "direct_observation",
        )
        self.assertEqual(
            cleaned["provenance"]["source_refs"],
            ["attest:source-example"],
        )

    def test_unknown_provenance_mode_fails_closed(self):
        value = packet()
        value["provenance"] = {
            "mode": "magic_truth_machine",
            "source_refs": [],
            "note": None,
        }
        with self.assertRaisesRegex(ValueError, "invalid provenance mode"):
            intake.validate_packet(value)

    def test_unknown_provenance_fields_fail_closed(self):
        value = packet()
        value["provenance"] = {
            "mode": "direct_observation",
            "source_refs": [],
            "note": None,
            "truth_score": 100,
        }
        with self.assertRaisesRegex(ValueError, "unknown provenance fields"):
            intake.validate_packet(value)


if __name__ == "__main__":
    unittest.main()
