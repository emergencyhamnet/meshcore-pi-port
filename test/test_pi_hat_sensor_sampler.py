from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'pi_hat_sensor_sampler.py'
SPEC = importlib.util.spec_from_file_location('pi_hat_sensor_sampler', SCRIPT)
SAMPLER = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(SAMPLER)


class PiHatSensorSamplerTests(unittest.TestCase):
    def test_collection_keeps_valid_sensor_groups_when_one_sensor_fails(self):
        with patch.object(SAMPLER, 'read_sht40', side_effect=OSError('sensor offline')), \
                patch.object(SAMPLER, 'read_lps22hh', return_value={'pressure_hpa': 1012.0, 'pressure_temperature_c': 40.0}), \
                patch.object(SAMPLER, 'read_ads1015', return_value={'vbat_v': 4.12}):
            result = SAMPLER.collect_snapshot(
                None,
                scales={'vin_v': 2, 'vout_v': 2, 'aux_v': 2, 'vbat_v': 3.5},
                sampled_at=datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(result['timestamp_unix'], 1793275200)
        self.assertEqual(result['measurements']['pressure_hpa'], 1012.0)
        self.assertEqual(result['measurements']['vbat_v'], 4.12)
        self.assertNotIn('temperature_c', result['measurements'])

    def test_env_snapshot_matches_native_reader_contract_and_omits_invalid(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'meshcore-pi-telemetry.env'
            snapshot = {
                'timestamp_unix': 1793275200,
                'measurements': {
                    'temperature_c': 22.5,
                    'humidity_pct': 45.0,
                    'pressure_hpa': 1011.2,
                    'pressure_temperature_c': 41.0,
                    'vbat_v': 4.1,
                    'vin_v': 5.0,
                    'aux_v': float('nan'),
                },
            }
            SAMPLER.write_snapshot(path, snapshot)

            fields = dict(line.split('=', 1) for line in path.read_text(encoding='utf-8').splitlines())
            if os.name != 'nt':
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

        self.assertEqual(fields, {
            'timestamp_unix': '1793275200',
            'temperature_c': '22.5000',
            'humidity_pct': '45.0000',
            'pressure_hpa': '1011.2000',
            'vbat_v': '4.1000',
        })
    def test_zero_voltage_is_preserved_and_bool_or_nonfinite_values_are_omitted(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'snapshot.env'
            SAMPLER.write_snapshot(path, {
                'timestamp_unix': 1,
                'measurements': {'vbat_v': 0.0, 'temperature_c': True, 'humidity_pct': float('inf')},
            })
            text = path.read_text(encoding='utf-8')

        self.assertIn('vbat_v=0.0000', text)
        self.assertNotIn('temperature_c=', text)
        self.assertNotIn('humidity_pct=', text)


if __name__ == '__main__':
    unittest.main()