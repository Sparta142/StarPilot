"""Accord 9G lead-car beep preference shared by Galaxy and the native feature presentation."""
from openpilot.starpilot.saved_document import commit_exact
from openpilot.starpilot.ui.feature_settings_state import FeatureRow


class HondaLeadBeepFeature:
  def __init__(self, owner):
    self.owner = owner

  def capability(self):
    from openpilot.starpilot.car.honda.lead_beep_preferences import qualified
    cp = self.owner.vehicle_params()
    try:
      if cp is None or not qualified(cp):
        return None
      return (str(cp.carFingerprint), int(cp.flags), bool(cp.openpilotLongitudinalControl),
              tuple((str(c.safetyModel), int(c.safetyParam)) for c in cp.safetyConfigs))
    except (AttributeError, TypeError, ValueError, OverflowError):
      return None

  def rows(self):
    from openpilot.starpilot.car.honda.lead_beep_preferences import KEY, CHOICES, DEFAULT, read_choice
    capability = self.capability()
    if capability is None:
      return ()
    value, raw, readable, valid = read_choice(self.owner.params)
    return (FeatureRow(KEY, "Lead Car Detected Beep", CHOICES[value] if valid else "Invalid saved choice", raw,
                       choices=tuple(CHOICES.values()), available=self.owner.authority("preferences") and readable,
                       capability=capability, repair_value="" if valid else CHOICES[DEFAULT], default_value=CHOICES[DEFAULT],
                       reason="Single chime when StarPilot speed control picks up a lead car, like the factory ACC. " +
                              "Applies during the drive."),)

  def apply(self, request):
    from openpilot.starpilot.car.honda.lead_beep_preferences import KEY, CHOICES, DEFAULT, read_choice
    value = next((code for code, label in CHOICES.items() if label == request.value), None)
    if request.key != KEY or value is None or request.related_source is not None or request.display_unit or request.direction:
      return False

    def authorized():
      capability = self.capability()
      _, raw, readable, valid = read_choice(self.owner.params)
      return (self.owner.authority("preferences") and bool(request.vehicle_fingerprint) and
              self.owner.vehicle_fingerprint() == request.vehicle_fingerprint and capability is not None and
              capability == request.capability and readable and raw == request.expected and (valid or value == DEFAULT))

    result = commit_exact(self.owner.params, key=KEY, max_bytes=8, raw=str(value).encode(), expected=request.expected,
                          authorized=authorized, temp_prefix=".honda-lead-beep-")
    return result.committed and result.verified
