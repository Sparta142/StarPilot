"""Accord 9G cluster HUD: mph set speed display and lane lines gated on lateral."""
import math

import pytest

from opendbc.can import CANParser
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.common.conversions import Conversions as CV
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, DBC


def _send(cc, is_metric=False):
  cp = CarInterface.get_params(CAR.HONDA_ACCORD_9G, gen_empty_fingerprint(), [], True, False, False)
  assert cp.openpilotLongitudinalControl
  ci = CarInterface(cp)
  ci.update([])
  ci.CS.is_metric = is_metric
  state = structs.CarState(vEgo=30.0)
  state.cruiseState.available = True
  ci.CS.out = state
  _, frames = ci.apply(cc.as_reader(), 10_000_000_000)
  return ci, frames


def _decode(ci, frames, msg, bus):
  decoder = CANParser(DBC[CAR.HONDA_ACCORD_9G][Bus.pt], [(msg, 10)], bus)
  assert decoder.update([(10_000_000_000, frames)])
  return decoder.vl[msg]


def _cluster_mph(kph):
  # Observed 9G cluster conversion: round(kph / 1.6), half up. Fits every in-car sample
  # (comma/cluster 25/24, 30/29, 50/49, 50/51, 52/53, 57/58, 60/59, 62/63, 67/68, 70/71, 75/74, 90/91 under floor(kph)).
  return math.floor(kph / 1.6 + 0.5)


# v_cruise_kph is 0.1 kph precision and off the mph grid: it starts at an integer kph from vEgo and steps 1.6 kph.
@pytest.mark.parametrize("v_cruise_kph", [x / 10 for x in range(300, 1451, 3)])
def test_imperial_cruise_speed_displays_setpoint(v_cruise_kph):
  cc = structs.CarControl(enabled=True, longActive=True, latActive=True)
  cc.hudControl.speedVisible = True
  cc.hudControl.setSpeed = float(v_cruise_kph * CV.KPH_TO_MS)  # as controlsd builds it
  ci, frames = _send(cc)
  kph = _decode(ci, frames, "ACC_HUD", ci.CC.CAN.pt)["CRUISE_SPEED"]
  comma_mph = round(v_cruise_kph * CV.KPH_TO_MPH)  # as the onroad UI shows it
  assert _cluster_mph(kph) == comma_mph
  assert abs(kph / 1.6 - comma_mph) <= 0.32  # margin against the cluster's exact factor


def test_metric_cruise_speed_unchanged():
  cc = structs.CarControl(enabled=True, longActive=True, latActive=True)
  cc.hudControl.speedVisible = True
  cc.hudControl.setSpeed = 112.6 * CV.KPH_TO_MS
  ci, frames = _send(cc, is_metric=True)
  assert _decode(ci, frames, "ACC_HUD", ci.CC.CAN.pt)["CRUISE_SPEED"] == 113


def test_hidden_cruise_speed_unchanged():
  cc = structs.CarControl(enabled=False)
  cc.hudControl.speedVisible = False
  ci, frames = _send(cc)
  # ACC_HUD only goes out with openpilot longitudinal; 255 = no speed
  assert _decode(ci, frames, "ACC_HUD", ci.CC.CAN.pt)["CRUISE_SPEED"] == 255


@pytest.mark.parametrize("lat_active", (False, True))
@pytest.mark.parametrize("lanes_visible", (False, True))
def test_lane_lines_follow_lateral_only(lat_active, lanes_visible):
  cc = structs.CarControl(enabled=True, longActive=True, latActive=lat_active)
  cc.hudControl.lanesVisible = lanes_visible  # controlsd sets this from lateral intent
  cc.hudControl.leftLaneVisible = cc.hudControl.rightLaneVisible = lanes_visible
  ci, frames = _send(cc)
  vl = _decode(ci, frames, "LKAS_HUD", ci.CC.CAN.lkas)
  assert bool(vl["SOLID_LANES"]) == (lat_active and lanes_visible)
  assert bool(vl["DASHED_LANES"]) == (lanes_visible and not lat_active)


@pytest.mark.parametrize("lat_active", (False, True))
def test_no_detected_lines_is_hollow(lat_active):
  cc = structs.CarControl(enabled=True, longActive=True, latActive=lat_active)
  cc.hudControl.lanesVisible = True
  cc.hudControl.leftLaneVisible = cc.hudControl.rightLaneVisible = False
  ci, frames = _send(cc)
  vl = _decode(ci, frames, "LKAS_HUD", ci.CC.CAN.lkas)
  assert not vl["SOLID_LANES"] and vl["DASHED_LANES"]
