#!/usr/bin/env python3
"""Interactive Accord 9G HUD probe. Run on the device with the car parked and ignition on:
  python3 -m opendbc.car.honda.hud_probe [--start SIGNAL] [--notes FILE]
Shows the signal being sent; type what you see on the cluster, Enter saves it and advances.
Commands at the prompt: (blank)=nothing seen, b=back, s=skip, r=resend, q=quit.
"""
import argparse
import os
import time

from opendbc.car.honda.hud_test import CYCLE, HUD_TEST_PATH


def set_signal(sig, val):
  tmp = HUD_TEST_PATH + ".tmp"
  with open(tmp, "w") as f:
    f.write(f"{sig}={val}")
  os.replace(tmp, HUD_TEST_PATH)


def clear():
  try:
    os.remove(HUD_TEST_PATH)
  except OSError:
    pass


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--start", help="signal name to start at")
  ap.add_argument("--notes", default=f"/data/honda_hud_notes_{time.strftime('%Y%m%d_%H%M%S')}.txt")
  args = ap.parse_args()

  i = 0
  if args.start:
    names = [s for s, _ in CYCLE]
    if args.start.upper() not in names:
      raise SystemExit(f"unknown signal; choices: {', '.join(dict.fromkeys(names))}")
    i = names.index(args.start.upper())

  print(f"Notes -> {args.notes}\nRequires: stationary, nothing engaged (otherwise the car ignores overrides).\n")
  try:
    while i < len(CYCLE):
      sig, val = CYCLE[i]
      set_signal(sig, val)
      print(f"[{i + 1}/{len(CYCLE)}] SENDING {sig}={val}")
      note = input("  what do you see? > ").strip()
      cmd = note.lower()
      if cmd == "q":
        break
      if cmd == "b":
        i = max(0, i - 1)
        continue
      if cmd == "r":
        continue
      if cmd != "s":
        with open(args.notes, "a") as f:
          f.write(f"{sig}={val}\t{note or '(nothing)'}\n")
          f.flush()
          os.fsync(f.fileno())
      i += 1
    else:
      print("Done.")
  except (KeyboardInterrupt, EOFError):
    print()
  finally:
    clear()
    print(f"Stopped sending. Notes: {args.notes}")


if __name__ == "__main__":
  main()
