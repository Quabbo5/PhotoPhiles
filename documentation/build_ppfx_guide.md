# Building .ppfx Effects — PhotoPhile Effect Format

A `.ppfx` file is a plain JSON file that describes an image effect as a
pipeline of operations. No code, no installs — just a text file you can
write in any editor, share with anyone, and drop straight into PhotoPhile.

---

## Minimal example

```json
{
  "schema_version": "1",
  "name": "My First Effect",
  "author": "yourname",
  "desc": "Inverts colors then adds a soft glow.",
  "tags": ["color", "glow"],
  "pipeline": [
    { "op": "negative" },
    { "op": "glow", "radius": 8, "strength": 0.4 }
  ]
}
```

Save it as `my_effect.ppfx` and drop it in the `effects/community/` folder.

---

## Full file structure

```json
{
  "schema_version": "1",
  "id": "optional-unique-id",
  "name": "Effect Name",
  "author": "yourname",
  "desc": "What this effect does.",
  "tags": ["tag1", "tag2"],
  "preview": "img/jpegs/something.jpg",
  "params": [
    { "name": "intensity", "type": "int",   "default": 45, "min": 0, "max": 180 },
    { "name": "strength",  "type": "float", "default": 0.5, "min": 0.0, "max": 1.0 }
  ],
  "pipeline": [
    { "op": "hue_shift", "amount": "$intensity" },
    { "op": "grain",     "strength": "$strength" }
  ]
}
```

| Field           | Required | Description                                      |
|-----------------|----------|--------------------------------------------------|
| schema_version  | yes      | always "1"                                       |
| name            | yes      | display name shown in the effect list            |
| pipeline        | yes      | list of op steps, executed top to bottom         |
| author          | no       | your username                                    |
| desc            | no       | short description                                |
| tags            | no       | list of strings for filtering                    |
| preview         | no       | path to a preview image                          |
| id              | no       | unique identifier (auto-generated from filename) |
| params          | no       | user-exposed parameters (see Parameters section) |

---

## Parameters

Params let users tweak your effect without editing the file.

```json
"params": [
  { "name": "amount", "type": "int",   "default": 30, "min": 0, "max": 180 },
  { "name": "blur",   "type": "float", "default": 5.0, "min": 0.5, "max": 20.0 }
]
```

Reference a param anywhere in the pipeline with `$name`:

```json
{ "op": "hue_shift", "amount": "$amount" },
{ "op": "gaussian_blur", "radius": "$blur" }
```

Inside a `loop`, the special variable `$i` gives you the current iteration index (starting at 0).

---

## All available ops

### Color

**hue_shift** — rotates all pixel hues
```json
{ "op": "hue_shift", "amount": 45 }
```
`amount` — degrees to rotate (0–360). Default: 10.

---

**saturation** — boosts or reduces color intensity
```json
{ "op": "saturation", "factor": 2.0 }
```
`factor` — multiplier. 1.0 = no change, 0 = greyscale, 2+ = vivid. Default: 1.5.

---

**brightness** — shifts all pixel values up or down
```json
{ "op": "brightness", "delta": 20 }
```
`delta` — amount to add (negative = darken). Default: 10.

---

**contrast** — expands or compresses the tonal range
```json
{ "op": "contrast", "factor": 1.5 }
```
`factor` — multiplier around midpoint 128. Default: 1.2.

---

**negative** — inverts all colors
```json
{ "op": "negative" }
```
No parameters.

---

**threshold** — maps pixels below a luma value to black, above to a color
```json
{ "op": "threshold", "value": 128, "color": [255, 0, 0] }
```
`value` — luma cutoff (0–255). Default: 128.
`color` — RGB array for bright pixels. Default: [255, 255, 255].

---

**posterize** — reduces the image to N flat tonal levels
```json
{ "op": "posterize", "levels": 4 }
```
`levels` — number of steps (2–16). Default: 4.

---

**duotone** — maps the image to a two-color gradient based on luma
```json
{ "op": "duotone", "dark": [20, 0, 40], "light": [255, 180, 0] }
```
`dark`  — RGB color for shadows. Default: [0, 0, 0].
`light` — RGB color for highlights. Default: [255, 255, 255].

---

**gradient_map** — maps luma to a multi-color gradient
```json
{ "op": "gradient_map", "colors": ["#000000", "#ff0050", "#ffffff"] }
```
`colors` — list of 2–8 hex color strings, from darkest to lightest. Default: black to white.

---

### Blur & Sharpen

**gaussian_blur** — smooth blur
```json
{ "op": "gaussian_blur", "radius": 8 }
```
`radius` — blur radius in pixels. Default: 5.

---

**box_blur** — fast flat blur
```json
{ "op": "box_blur", "radius": 6 }
```
`radius` — blur radius. Default: 5.

---

**sharpen** — sharpens edges
```json
{ "op": "sharpen" }
```
No parameters.

---

**edge_detect** — highlights edges, darkens flat areas
```json
{ "op": "edge_detect" }
```
No parameters.

---

**emboss** — gives the image a raised, chiselled look
```json
{ "op": "emboss" }
```
No parameters.

---

### Warp & Distortion

**ripple** — sine wave distortion
```json
{ "op": "ripple", "amplitude": 15, "wavelength": 40 }
```
`amplitude`  — how far pixels shift. Default: 10.
`wavelength` — wave size in pixels. Default: 30.

---

**vortex** — swirl distortion around a point
```json
{ "op": "vortex", "strength": 500, "cx_frac": 0.5, "cy_frac": 0.5 }
```
`strength` — swirl intensity (negative = opposite direction). Default: 300.
`cx_frac`  — centre X as a fraction of width (0.0–1.0). Default: 0.5.
`cy_frac`  — centre Y as a fraction of height (0.0–1.0). Default: 0.5.

---

**polar_invert** — folds the image inside-out from the centre
```json
{ "op": "polar_invert" }
```
No parameters.

---

**channel_roll** — shifts one color channel independently
```json
{ "op": "channel_roll", "channel": "r", "dx": 20, "dy": 0 }
```
`channel` — which channel: "r", "g", or "b". Default: "r".
`dx`      — horizontal shift in pixels. Default: 0.
`dy`      — vertical shift in pixels. Default: 0.

---

**pixelate** — reduces resolution into visible blocks
```json
{ "op": "pixelate", "size": 12 }
```
`size` — block size in pixels. Default: 8.

---

### Noise & Texture

**grain** — adds monochrome noise
```json
{ "op": "grain", "strength": 0.25 }
```
`strength` — blend amount (0.0–1.0). Default: 0.3.

---

**color_grain** — adds full-color random noise
```json
{ "op": "color_grain", "strength": 0.2 }
```
`strength` — blend amount (0.0–1.0). Default: 0.3.

---

**glow** — adds a luminous halo
```json
{ "op": "glow", "radius": 12, "strength": 0.5 }
```
`radius`   — blur radius for the glow spread. Default: 10.
`strength` — how much glow to add on top. Default: 0.3.

---

### Compositing (Buffers)

Buffers let you save the image at any point in the pipeline and blend it
back in later. Think of them as named snapshots.

**save_buffer** — saves the current image state into a named slot
```json
{ "op": "save_buffer", "name": "original" }
```

**load_buffer** — restores a saved buffer as the current image
```json
{ "op": "load_buffer", "name": "original" }
```

**blend** — mixes the current image with a saved buffer
```json
{ "op": "blend", "source": "original", "mode": "screen", "opacity": 0.5 }
```
`source`  — name of the saved buffer to blend from.
`opacity` — how strongly the source is blended in (0.0–1.0). Default: 0.5.
`mode`    — blend mode. Options: `normal`, `multiply`, `screen`, `add`, `subtract`, `overlay`. Default: normal.

---

### Control Flow

**loop** — repeats a sub-pipeline N times. Use `$i` for the iteration index.
```json
{
  "op": "loop",
  "times": 3,
  "pipeline": [
    { "op": "hue_shift", "amount": 30 },
    { "op": "ripple", "amplitude": 5 }
  ]
}
```
`times` — number of repetitions (1–20). Default: 1.

---

**if** — runs a sub-pipeline only when a param exceeds a threshold
```json
{
  "op": "if",
  "param": "intensity",
  "gt": 50,
  "pipeline": [
    { "op": "grain", "strength": 0.4 }
  ]
}
```
`param` — name of a param from your `params` block.
`gt`    — the sub-pipeline runs only if `param > gt`.

---

## Full examples

### Chromatic aberration
```json
{
  "schema_version": "1",
  "name": "Chromatic Aberration",
  "author": "yourname",
  "desc": "RGB channel split with colour shift.",
  "tags": ["color", "warp"],
  "params": [
    { "name": "spread", "type": "int", "default": 20, "min": 0, "max": 80 }
  ],
  "pipeline": [
    { "op": "channel_roll", "channel": "r", "dx": "$spread" },
    { "op": "channel_roll", "channel": "b", "dx": -20 },
    { "op": "hue_shift", "amount": 15 }
  ]
}
```

### Dreamy soft glow
```json
{
  "schema_version": "1",
  "name": "Dreamy",
  "author": "yourname",
  "desc": "Warm glow blended back over the original.",
  "tags": ["glow", "blur", "light"],
  "params": [
    { "name": "warmth", "type": "int", "default": 10, "min": 0, "max": 40 }
  ],
  "pipeline": [
    { "op": "save_buffer", "name": "sharp" },
    { "op": "brightness", "delta": "$warmth" },
    { "op": "gaussian_blur", "radius": 12 },
    { "op": "blend", "source": "sharp", "mode": "screen", "opacity": 0.5 }
  ]
}
```

### Electric palette
```json
{
  "schema_version": "1",
  "name": "Electric",
  "author": "yourname",
  "desc": "Posterized with a neon colour map.",
  "tags": ["color", "posterize"],
  "pipeline": [
    { "op": "posterize", "levels": 5 },
    { "op": "gradient_map", "colors": ["#000000", "#ff0050", "#00ffb4", "#5000ff", "#ffdc00"] }
  ]
}
```

### Layered vortex (loop + $i)
```json
{
  "schema_version": "1",
  "name": "Triple Vortex",
  "author": "yourname",
  "desc": "Three vortexes applied at increasing strength.",
  "tags": ["warp", "chaos"],
  "pipeline": [
    {
      "op": "loop",
      "times": 3,
      "pipeline": [
        { "op": "vortex", "strength": 200 }
      ]
    }
  ]
}
```

---

## Rules and limits

- Pipeline max: **256 steps**
- Loop max: **20 iterations** — no nested loops
- File size max: **64 KB**
- `if` conditions: only `gt` (greater than) is supported
- Param references: `$name` for any declared param, `$i` inside loops only
- Unknown ops are rejected at load time — the file will not run

---

## Where to put your files

Drop `.ppfx` files into:
```
PhotoPhile/effects/community/
```

They load automatically on startup alongside the built-in effects.
