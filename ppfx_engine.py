"""
ppfx_engine.py — PhotoPhile Effect (.ppfx) pipeline executor.

STASHED FEATURE — not connected to the main interface yet.

Integration: when ready, add to effect_registry.py:

    from ppfx_engine import load_ppfx_folder

    def load_effects(app, csv_path=None):
        effects = [...]            # existing CSV load
        effects += load_ppfx_folder(app, "effects/community")
        return effects
"""

import json
import os
import numpy as np
from PIL import Image, ImageFilter

try:
    import cv2
    _CV2 = True
except ImportError:
    _CV2 = False


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

MAX_FILE_BYTES = 64 * 1024   # 64 KB
MAX_STEPS      = 256
MAX_LOOP_TIMES = 20

ALLOWED_OPS = frozenset({
    # color
    "hue_shift", "saturation", "brightness", "contrast",
    "negative", "threshold", "posterize", "duotone", "gradient_map",
    # blur / sharpen
    "gaussian_blur", "box_blur", "sharpen", "edge_detect", "emboss",
    # warp / distortion
    "ripple", "vortex", "polar_invert", "channel_roll", "pixelate",
    # noise / texture
    "grain", "color_grain", "glow",
    # compositing
    "save_buffer", "load_buffer", "blend",
    # control flow
    "loop", "if",
})


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate(data):
    for field in ("schema_version", "name", "pipeline"):
        if field not in data:
            raise ValueError(f".ppfx missing required field: '{field}'")
    if not isinstance(data["pipeline"], list):
        raise ValueError("'pipeline' must be a list")
    if len(data["pipeline"]) > MAX_STEPS:
        raise ValueError(f"pipeline exceeds {MAX_STEPS} step limit")
    for i, step in enumerate(data["pipeline"]):
        _validate_step(step, i)
    for p in data.get("params", []):
        if "name" not in p or "default" not in p:
            raise ValueError(f"param missing 'name' or 'default': {p}")
        if "min" in p and "max" in p and p["min"] > p["max"]:
            raise ValueError(f"param '{p['name']}': min > max")


def _validate_step(step, idx, inside_loop=False):
    if "op" not in step:
        raise ValueError(f"step {idx} is missing 'op'")
    op = step["op"]
    if op not in ALLOWED_OPS:
        raise ValueError(f"step {idx}: unknown op '{op}'")
    if op == "loop":
        times = step.get("times", 1)
        if not isinstance(times, int) or not (1 <= times <= MAX_LOOP_TIMES):
            raise ValueError(f"loop 'times' must be an integer between 1 and {MAX_LOOP_TIMES}")
        if inside_loop:
            raise ValueError("nested loops are not allowed")
        for j, sub in enumerate(step.get("pipeline", [])):
            _validate_step(sub, j, inside_loop=True)
    if op == "if":
        for j, sub in enumerate(step.get("pipeline", [])):
            _validate_step(sub, j, inside_loop=inside_loop)


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------

def _resolve(value, params, loop_i=None):
    """Resolve a $param reference to its value, or return the value as-is."""
    if isinstance(value, str) and value.startswith("$"):
        key = value[1:]
        if key == "i":
            return loop_i if loop_i is not None else 0
        if key not in params:
            raise ValueError(f"undefined param reference: ${key}")
        return params[key]
    return value


def _p(step, key, params, default=None, loop_i=None):
    return _resolve(step.get(key, default), params, loop_i)


# ---------------------------------------------------------------------------
# Op implementations
# ---------------------------------------------------------------------------

def _op_hue_shift(arr, step, params, loop_i, **__):
    if not _CV2:
        return arr
    amount = _p(step, "amount", params, 10, loop_i)
    rgb = np.clip(arr[..., :3], 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 0] = (hsv[..., 0] + amount / 2) % 180
    arr[..., :3] = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    return arr


def _op_saturation(arr, step, params, loop_i, **__):
    if not _CV2:
        return arr
    factor = _p(step, "factor", params, 1.5, loop_i)
    rgb = np.clip(arr[..., :3], 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * factor, 0, 255)
    arr[..., :3] = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
    return arr


def _op_brightness(arr, step, params, loop_i, **__):
    delta = _p(step, "delta", params, 10, loop_i)
    arr[..., :3] = np.clip(arr[..., :3] + delta, 0, 255)
    return arr


def _op_contrast(arr, step, params, loop_i, **__):
    factor = _p(step, "factor", params, 1.2, loop_i)
    arr[..., :3] = np.clip((arr[..., :3] - 128) * factor + 128, 0, 255)
    return arr


def _op_negative(arr, **__):
    arr[..., :3] = 255 - arr[..., :3]
    return arr


def _op_threshold(arr, step, params, loop_i, **__):
    value = _p(step, "value", params, 128, loop_i)
    color = _p(step, "color", params, [255, 255, 255], loop_i)
    luma  = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
    arr[luma <  value, :3] = 0
    arr[luma >= value, :3] = color
    return arr


def _op_posterize(arr, step, params, loop_i, **__):
    levels    = max(2, int(_p(step, "levels", params, 4, loop_i)))
    step_size = 255 / (levels - 1)
    arr[..., :3] = np.round(arr[..., :3] / step_size) * step_size
    return np.clip(arr, 0, 255)


def _op_duotone(arr, step, params, loop_i, **__):
    dark  = _p(step, "dark",  params, [0, 0, 0],       loop_i)
    light = _p(step, "light", params, [255, 255, 255],  loop_i)
    luma  = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]) / 255
    for c in range(3):
        arr[..., c] = dark[c] * (1 - luma) + light[c] * luma
    return np.clip(arr, 0, 255)


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i+2], 16) for i in (0, 2, 4)]


def _op_gradient_map(arr, step, params, loop_i, **__):
    colors  = _p(step, "colors", params, ["#000000", "#ffffff"], loop_i)
    palette = [_hex_to_rgb(c) for c in colors]
    n       = len(palette) - 1
    luma    = np.clip(0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2], 0, 255) / 255
    t       = luma * n
    idx     = np.clip(t.astype(np.int32), 0, n - 1)
    frac    = (t - idx)[..., np.newaxis]
    p0      = np.array(palette)[idx]
    p1      = np.array(palette)[np.clip(idx + 1, 0, n)]
    arr[..., :3] = np.clip(p0 * (1 - frac) + p1 * frac, 0, 255)
    return arr


def _apply_pil_filter(arr, pil_filter):
    """Apply a PIL filter to RGB channels only, leaving alpha untouched."""
    rgb = Image.fromarray(np.clip(arr[..., :3], 0, 255).astype(np.uint8))
    result = np.array(rgb.filter(pil_filter)).astype(np.float32)
    out = arr.copy()
    out[..., :3] = result
    return out


def _op_gaussian_blur(arr, step, params, loop_i, **__):
    return _apply_pil_filter(arr, ImageFilter.GaussianBlur(radius=_p(step, "radius", params, 5, loop_i)))


def _op_box_blur(arr, step, params, loop_i, **__):
    return _apply_pil_filter(arr, ImageFilter.BoxBlur(radius=_p(step, "radius", params, 5, loop_i)))


def _op_sharpen(arr, **__):
    return _apply_pil_filter(arr, ImageFilter.SHARPEN)


def _op_edge_detect(arr, **__):
    return _apply_pil_filter(arr, ImageFilter.FIND_EDGES)


def _op_emboss(arr, **__):
    return _apply_pil_filter(arr, ImageFilter.EMBOSS)


def _op_ripple(arr, step, params, loop_i, **__):
    amplitude  = _p(step, "amplitude",  params, 10, loop_i)
    wavelength = _p(step, "wavelength", params, 30, loop_i)
    _H, _W = arr.shape[:2]
    xx, yy = np.meshgrid(np.arange(_W), np.arange(_H))
    src_x = np.clip(xx + (amplitude * np.sin(2 * np.pi * yy / wavelength)).astype(np.int32), 0, _W - 1)
    src_y = np.clip(yy + (amplitude * np.sin(2 * np.pi * xx / wavelength)).astype(np.int32), 0, _H - 1)
    return arr[src_y, src_x]


def _op_vortex(arr, step, params, loop_i, **__):
    strength = _p(step, "strength", params, 300,  loop_i)
    cx_frac  = _p(step, "cx_frac",  params, 0.5,  loop_i)
    cy_frac  = _p(step, "cy_frac",  params, 0.5,  loop_i)
    _H, _W   = arr.shape[:2]
    cx, cy   = _W * cx_frac, _H * cy_frac
    y_c, x_c = np.mgrid[0:_H, 0:_W].astype(np.float32)
    dy   = y_c - cy
    dx   = x_c - cx
    dist = np.sqrt(dx**2 + dy**2) + 0.001
    angle = np.arctan2(dy, dx) + (strength / (dist + 1))
    src_x = np.clip((cx + dist * np.cos(angle)).astype(np.int32), 0, _W - 1)
    src_y = np.clip((cy + dist * np.sin(angle)).astype(np.int32), 0, _H - 1)
    return arr[src_y, src_x]


def _op_polar_invert(arr, **__):
    _H, _W   = arr.shape[:2]
    cy, cx   = _H / 2, _W / 2
    y_c, x_c = np.mgrid[0:_H, 0:_W].astype(np.float32)
    dy       = y_c - cy
    dx       = x_c - cx
    dist     = np.sqrt(dx**2 + dy**2) + 0.001
    max_dist = np.sqrt(cx**2 + cy**2)
    inv_dist = np.clip(max_dist**2 / (dist + 1), 0, max_dist)
    angle    = np.arctan2(dy, dx)
    src_x    = np.clip((cx + inv_dist * np.cos(angle)).astype(np.int32), 0, _W - 1)
    src_y    = np.clip((cy + inv_dist * np.sin(angle)).astype(np.int32), 0, _H - 1)
    return arr[src_y, src_x]


def _op_channel_roll(arr, step, params, loop_i, **__):
    ch_map = {"r": 0, "g": 1, "b": 2}
    ch  = ch_map.get(str(_p(step, "channel", params, "r", loop_i)).lower(), 0)
    dx  = int(_p(step, "dx", params, 0, loop_i))
    dy  = int(_p(step, "dy", params, 0, loop_i))
    arr[..., ch] = np.roll(arr[..., ch], dx, axis=1)
    arr[..., ch] = np.roll(arr[..., ch], dy, axis=0)
    return arr


def _op_pixelate(arr, step, params, loop_i, **__):
    size  = max(1, int(_p(step, "size", params, 8, loop_i)))
    _H, _W = arr.shape[:2]
    rgb   = Image.fromarray(np.clip(arr[..., :3], 0, 255).astype(np.uint8))
    small = rgb.resize((_W // size, _H // size), Image.NEAREST)
    out   = arr.copy()
    out[..., :3] = np.array(small.resize((_W, _H), Image.NEAREST)).astype(np.float32)
    return out


def _op_grain(arr, step, params, loop_i, **__):
    strength = _p(step, "strength", params, 0.3, loop_i)
    _H, _W   = arr.shape[:2]
    noise    = np.random.randint(0, 256, (_H, _W), dtype=np.uint8).astype(np.float32)
    for c in range(min(3, arr.shape[2])):
        arr[..., c] = np.clip(arr[..., c] * (1 - strength) + noise * strength, 0, 255)
    return arr


def _op_color_grain(arr, step, params, loop_i, **__):
    strength = _p(step, "strength", params, 0.3, loop_i)
    _H, _W   = arr.shape[:2]
    noise    = np.random.randint(0, 256, (_H, _W, 3), dtype=np.uint8).astype(np.float32)
    arr[..., :3] = np.clip(arr[..., :3] * (1 - strength) + noise * strength, 0, 255)
    return arr


def _op_glow(arr, step, params, loop_i, **__):
    radius   = _p(step, "radius",   params, 10,  loop_i)
    strength = _p(step, "strength", params, 0.3, loop_i)
    img  = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    blur = np.array(img.filter(ImageFilter.GaussianBlur(radius=radius))).astype(np.float32)
    return np.clip(arr + blur * strength, 0, 255)


def _op_blend(arr, step, params, loop_i, buffers, **__):
    name = step.get("source", "")
    if name not in buffers:
        raise ValueError(f"blend: buffer '{name}' not found — save_buffer it first")
    src     = buffers[name].astype(np.float32)
    opacity = float(_p(step, "opacity", params, 0.5, loop_i))
    mode    = str(step.get("mode", "normal")).lower()

    if mode == "multiply":
        blended = arr * src / 255
    elif mode == "screen":
        blended = 255 - (255 - arr) * (255 - src) / 255
    elif mode == "add":
        blended = np.clip(arr + src, 0, 255)
    elif mode == "subtract":
        blended = np.clip(arr - src, 0, 255)
    elif mode == "overlay":
        blended = np.where(arr < 128, 2 * arr * src / 255, 255 - 2 * (255 - arr) * (255 - src) / 255)
    else:  # normal
        blended = src

    arr[..., :3] = np.clip(arr[..., :3] * (1 - opacity) + blended[..., :3] * opacity, 0, 255)
    return arr


# ---------------------------------------------------------------------------
# Op dispatch table
# ---------------------------------------------------------------------------

_OP_TABLE = {
    "hue_shift":    _op_hue_shift,
    "saturation":   _op_saturation,
    "brightness":   _op_brightness,
    "contrast":     _op_contrast,
    "negative":     _op_negative,
    "threshold":    _op_threshold,
    "posterize":    _op_posterize,
    "duotone":      _op_duotone,
    "gradient_map": _op_gradient_map,
    "gaussian_blur": _op_gaussian_blur,
    "box_blur":     _op_box_blur,
    "sharpen":      _op_sharpen,
    "edge_detect":  _op_edge_detect,
    "emboss":       _op_emboss,
    "ripple":       _op_ripple,
    "vortex":       _op_vortex,
    "polar_invert": _op_polar_invert,
    "channel_roll": _op_channel_roll,
    "pixelate":     _op_pixelate,
    "grain":        _op_grain,
    "color_grain":  _op_color_grain,
    "glow":         _op_glow,
    "blend":        _op_blend,
}


# ---------------------------------------------------------------------------
# Pipeline executor
# ---------------------------------------------------------------------------

def _run_pipeline(pipeline, arr, params, buffers, loop_i=None):
    for step in pipeline:
        op = step["op"]

        if op == "save_buffer":
            buffers[step.get("name", "default")] = arr.copy()
            continue

        if op == "load_buffer":
            name = step.get("name", "default")
            if name not in buffers:
                raise ValueError(f"load_buffer: '{name}' not found")
            arr = buffers[name].copy()
            continue

        if op == "loop":
            sub = step.get("pipeline", [])
            for i in range(int(step.get("times", 1))):
                arr = _run_pipeline(sub, arr, params, buffers, loop_i=i)
            continue

        if op == "if":
            param_key = step.get("param", "")
            threshold = step.get("gt", None)
            sub       = step.get("pipeline", [])
            actual    = params.get(param_key, 0)
            if threshold is None or actual > threshold:
                arr = _run_pipeline(sub, arr, params, buffers, loop_i=loop_i)
            continue

        fn = _OP_TABLE.get(op)
        if fn is None:
            raise ValueError(f"op '{op}' has no implementation")
        arr = fn(arr, step=step, params=params, loop_i=loop_i, buffers=buffers)

    return arr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_ppfx(path):
    """
    Load and validate a .ppfx file.
    Returns a callable:  fn(image: PIL.Image, **kwargs) -> PIL.Image
    """
    if os.path.getsize(path) > MAX_FILE_BYTES:
        raise ValueError(f".ppfx exceeds {MAX_FILE_BYTES // 1024} KB limit: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    _validate(data)

    param_defs = data.get("params", [])
    pipeline   = data["pipeline"]

    def fn(image, **kwargs):
        params = {}
        for p in param_defs:
            val = kwargs.get(p["name"], p["default"])
            val = max(p.get("min", val), val)
            val = min(p.get("max", val), val)
            params[p["name"]] = val
        arr = np.array(image).astype(np.float32)
        arr = _run_pipeline(pipeline, arr, params, buffers={})
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    return fn


def load_ppfx_folder(app, folder):
    """
    Scan a folder for .ppfx files, load each one, and return a list of
    effect dicts in the same shape as effect_registry.load_effects().

    Drop-in integration — pass the result to effect_registry:
        effects += load_ppfx_folder(app, "effects/community")
    """
    if not os.path.isdir(folder):
        return []

    effects = []
    for fname in sorted(os.listdir(folder)):
        if not fname.endswith(".ppfx"):
            continue
        path = os.path.join(folder, fname)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            _validate(data)
            ppfx_fn = load_ppfx(path)

            # wrap so it fits the existing fn(**kwargs) → modifies app.current_image pattern
            def make_fn(pfn):
                def bound(**kwargs):
                    app.current_image = pfn(app.current_image, **kwargs)
                return bound

            effects.append({
                "id":      data.get("id", os.path.splitext(fname)[0]),
                "name":    data["name"],
                "author":  data.get("author", "unknown"),
                "desc":    data.get("desc", ""),
                "tags":    data.get("tags", []),
                "preview": data.get("preview", ""),
                "fn":      make_fn(ppfx_fn),
                "params":  data.get("params", []),
            })
        except Exception as exc:
            print(f"[ppfx_engine] skipping '{fname}': {exc}")

    return effects
