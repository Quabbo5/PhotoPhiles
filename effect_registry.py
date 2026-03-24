import csv
import json
import os
from ppfx_engine import load_ppfx_folder

# ---------------------------------------------------------------------------
# Effect Registry
# ---------------------------------------------------------------------------
# Maps fn_name strings (as stored in effects.csv) to bound methods on the app.
# When you add a new Python effect:
#   1. Write the method in effects_mixin.py
#   2. Add one line here
#   3. Add one row to effects.csv
# Nothing else needs to change.
# ---------------------------------------------------------------------------

def _build_registry(app):
    return {
        "posterize_1bit":     app._posterize_1bit,
        "posterize_3bit":     app._posterize_3bit,
        "negative":           app._negative,
        "glow":               app._glow,
        "color_grain":        app._color_grain,
        "duotone_threshold":  app._duotone_threshold,
        "hue_shift":          app._hue_shift,
        "brightness_up":      app._brightness_up,
        "brightness_down":    app._brightness_down,
        "ripple":             app._ripple,
        "chaos":              app._chaos,
        "gate_of_azrael":     app._gate_of_azrael,
        "life_is_worth_living": app._life_is_worth_living,

        # C++ backed effects go here too — same interface, different backing:
        # "fast_blur": app._cpp_fast_blur,
    }


def load_effects(app, csv_path=None):
    """
    Load effects from effects.csv and resolve each fn_name to a callable.
    Returns a list of effect dicts in the same shape the app already expects.
    """
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), "effects.csv")

    registry = _build_registry(app)
    effects  = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fn_name = row["fn_name"].strip()

            if fn_name not in registry:
                print(f"[effect_registry] WARNING: unknown fn_name '{fn_name}' — skipping.")
                continue

            effect = {
                "id":      row["id"].strip(),
                "name":    row["name"].strip(),
                "author":  row["author"].strip(),
                "desc":    row["desc"].strip(),
                "tags":    [t.strip() for t in row["tags"].split("|") if t.strip()],
                "preview": row["preview"].strip(),
                "fn":      registry[fn_name],
                "params":  json.loads(row["params"].strip() or "[]"),
            }
            effects.append(effect)

    effects += load_ppfx_folder(app, os.path.join(os.path.dirname(__file__), "effects/community"))
    return effects
