"""Accord 9G: on/off switch for the OEM-style single beep when ACC acquires a lead car."""
from openpilot.starpilot.saved_source import read_saved

KEY = "HondaLeadBeep"
CHOICES = {0: "Off", 1: "On"}
DEFAULT = 1


def qualified(cp):
  """The Accord 9G with StarPilot speed control: the only Honda that sends the lead beep."""
  from opendbc.car.honda.values import CAR
  try:
    return bool(cp.brand == "honda" and cp.carFingerprint == CAR.HONDA_ACCORD_9G and cp.openpilotLongitudinalControl and
                not cp.passive and not cp.dashcamOnly and not cp.notCar)
  except (AttributeError, TypeError, ValueError):
    return False


def read_choice(params):
  """(value, raw, readable, valid). A missing or invalid saved value reads as the default (On)."""
  raw, readable = read_saved(params, KEY, 8)
  valid = readable and raw in (None, b"0", b"1")
  value = (0 if raw == b"0" else 1) if valid else DEFAULT
  return value, raw, readable, valid


class LeadBeepPreference:
  """Controller input: card refreshes it once a second, so the switch applies during the drive."""
  def __init__(self, params):
    self.params = params
    self.enabled = bool(read_choice(params)[0])

  def refresh_settings(self):
    self.enabled = bool(read_choice(self.params)[0])

  def update(self) -> bool:
    return self.enabled
