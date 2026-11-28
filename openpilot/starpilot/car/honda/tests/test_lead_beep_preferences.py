"""Accord 9G lead-car beep switch: saved preference, settings row, and controller input."""
from pathlib import Path

import pytest

from opendbc.car import gen_empty_fingerprint
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.starpilot.car.honda.lead_beep_preferences import KEY, LeadBeepPreference, qualified, read_choice
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest
from openpilot.starpilot.ui.honda_lead_beep_feature import HondaLeadBeepFeature


class FileParams:
  def __init__(self, root):
    self.root = Path(root)

  def get_param_path(self, key):
    return str(self.root / key)


class Owner:
  def __init__(self, params, cp, authorized=True):
    self.params, self.cp, self.authorized = params, cp, authorized

  def vehicle_params(self):
    return self.cp

  def vehicle_fingerprint(self):
    return str(self.cp.carFingerprint)

  def authority(self, group):
    return self.authorized and group == "preferences"


def accord(long=True):
  cp = CarInterface.get_params(CAR.HONDA_ACCORD_9G, gen_empty_fingerprint(), [], True, False, False)
  cp.openpilotLongitudinalControl = long
  return cp


def change(o, value):
  row, = HondaLeadBeepFeature(o).rows()
  return HondaLeadBeepFeature(o).apply(FeatureSettingsRequest(KEY, row.source, value, vehicle_fingerprint=o.vehicle_fingerprint(),
                                                              capability=row.capability))


def test_qualified_only_with_starpilot_long():
  assert qualified(accord())
  assert not qualified(accord(long=False))
  other = CarInterface.get_params(CAR.HONDA_CIVIC, gen_empty_fingerprint(), [], True, False, False)
  assert not qualified(other)


def test_missing_or_invalid_reads_as_on(tmp_path):
  params = FileParams(tmp_path)
  assert read_choice(params)[0] == 1
  Path(params.get_param_path(KEY)).write_bytes(b"x")
  value, _, _, valid = read_choice(params)
  assert value == 1 and not valid
  Path(params.get_param_path(KEY)).write_bytes(b"0")
  assert read_choice(params)[0] == 0


def test_row_hidden_without_starpilot_long(tmp_path):
  assert HondaLeadBeepFeature(Owner(FileParams(tmp_path), accord(long=False))).rows() == ()


def test_toggle_round_trip_and_live_refresh(tmp_path):
  params = FileParams(tmp_path)
  o = Owner(params, accord())
  row, = HondaLeadBeepFeature(o).rows()
  assert row.value == row.default_value == "On" and row.available

  pref = LeadBeepPreference(params)
  assert pref.update()
  assert change(o, "Off")
  assert Path(params.get_param_path(KEY)).read_bytes() == b"0"
  assert pref.update()  # takes effect on the next card refresh
  pref.refresh_settings()
  assert not pref.update()
  assert change(o, "On")
  pref.refresh_settings()
  assert pref.update()


def test_change_refused_without_authority(tmp_path):
  o = Owner(FileParams(tmp_path), accord(), authorized=False)
  assert not HondaLeadBeepFeature(o).rows()[0].available
  assert not change(o, "Off")


def test_controller_gets_input_only_when_qualified(tmp_path):
  try:
    from openpilot.starpilot.controller_extensions import configure_controller
  except ImportError as e:  # native msgq not built for this host
    pytest.skip(str(e))
  params = FileParams(tmp_path)
  ci = CarInterface(accord())
  configure_controller(ci, params)
  assert isinstance(ci.CC.lead_beep_input, LeadBeepPreference)

  stock = CarInterface(accord(long=False))
  configure_controller(stock, params)
  assert stock.CC.lead_beep_input is None

