"""Parked-only HUD signal probe for the Accord 9G cluster.

Write "SIGNAL" or "SIGNAL=value" (comma-separated for several) to HUD_TEST_PATH, e.g.
  echo -n ACC_PROBLEM > /data/honda_hud_test
  echo -n "LKAS_PROBLEM,HUD_LEAD=3" > /data/honda_hud_test
  echo -n cycle > /data/honda_hud_test     # step through every probe signal, 3 s each (logged to HUD_TEST_LOG)
  rm /data/honda_hud_test                  # off
Ignored unless stationary, not engaged, and not in drive-engaged state.
"""
import os

HUD_TEST_PATH = os.environ.get("HONDA_HUD_TEST_PATH", "/data/honda_hud_test")
HUD_TEST_LOG = HUD_TEST_PATH + ".log"
CYCLE_FRAMES = 30  # HUD frames (every 10 control frames = 10 Hz) -> 3 s per signal

ACC_HUD_PROBES = ("ACC_PROBLEM", "FCM_PROBLEM", "FCM_OFF", "FCM_OFF_2", "RADAR_OBSTRUCTED", "BRAKE_SYSTEM_ICON",
                  "DTC_MODE", "CRUISE_CONTROL_LABEL", "BOH_3", "BOH_4", "BOH_5")
LKAS_HUD_PROBES = ("LKAS_PROBLEM", "LKAS_OFF", "CLEAN_WINDSHIELD", "CAM_TEMP_HIGH", "DTC", "DASHED_LANES",
                   "RDM_PROBLEM", "RDM_HUD", "RDM_HUD_2", "RDM_ON", "RDM_ON_2")
CYCLE = tuple((s, 1) for s in ACC_HUD_PROBES + LKAS_HUD_PROBES) + (("HUD_LEAD", 3), ("CHIME", 1), ("CHIME", 2), ("BEEP", 1), ("BEEP", 2))


def _parse(text):
  out = {}
  for item in text.split(","):
    item = item.strip()
    if item:
      name, _, val = item.partition("=")
      out[name.strip().upper()] = int(val) if val else 1
  return out


class HudTest:
  def __init__(self):
    self.n = 0
    self.last = None

  def overrides(self, active_ok):
    """Returns {signal: value} for this HUD frame; empty when disabled or unsafe."""
    self.n += 1
    if not active_ok:
      return {}
    try:
      with open(HUD_TEST_PATH) as f:
        text = f.read().strip()
    except OSError:
      self.last = None
      return {}
    try:
      if text.lower() == "cycle":
        sig, val = CYCLE[(self.n // CYCLE_FRAMES) % len(CYCLE)]
        cur = {sig: val}
      else:
        cur = _parse(text)
    except ValueError:
      return {}
    if cur != self.last:
      self.last = cur
      try:
        with open(HUD_TEST_LOG, "a") as f:
          f.write(f"{cur}\n")
      except OSError:
        pass
    return cur
