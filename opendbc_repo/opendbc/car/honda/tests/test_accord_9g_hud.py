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


@pytest.mark.parametrize("mph", range(20, 91))
def test_imperial_cruise_speed_displays_setpoint(mph):
  cc = structs.CarControl(enabled=True, longActive=True, latActive=True)
  cc.hudControl.speedVisible = True
  cc.hudControl.setSpeed = float(mph * CV.MPH_TO_KPH * CV.KPH_TO_MS)  # as controlsd builds it
  ci, frames = _send(cc)
  kph = _decode(ci, frames, "ACC_HUD", ci.CC.CAN.pt)["CRUISE_SPEED"]
  # Assumes the cluster rounds its kph->mph conversion up; it must land on the setpoint.
  assert math.ceil(kph * CV.KPH_TO_MPH) == mph


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
  cc.hudControl.lanesVisible = lanes_visible  # controlsd sets this from enabled
  ci, frames = _send(cc)
  assert bool(_decode(ci, frames, "LKAS_HUD", ci.CC.CAN.lkas)["SOLID_LANES"]) == lat_active
