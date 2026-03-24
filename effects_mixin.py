import threading
from tkinter import *
from PIL import Image, ImageFilter, ImageTk
import numpy as np
import cv2


class EffectsMixin:

    # ------------------------------------------------------------------
    # Core dispatch
    # ------------------------------------------------------------------

    def _apply_effect(self, index, **kwargs):
        if self._wiki_open:
            self._log("Close the wiki first (Esc) before applying effects.", "err")
            return
        if getattr(self, "_effect_running", False):
            self._log("An effect is already running, please wait.", "err")
            return

        effect = self.EFFECTS[index]
        for p in effect.get("params", []):
            kwargs.setdefault(p["name"], p["default"])

        self._log(f"[{effect['id']}] {effect['name']} – applying...", "prompt")
        self._set_ui_busy(True)

        def _worker():
            try:
                effect["fn"](**kwargs)
                resized = self.current_image.resize((800, 800))
            except Exception as exc:
                self.root.after(0, lambda e=exc: self._on_effect_error(effect, e))
                return
            self.root.after(0, lambda img=resized: self._on_effect_done(effect, img))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_effect_done(self, effect, resized):
        new_canvas = ImageTk.PhotoImage(resized)
        self.image_label.config(image=new_canvas)
        self.image_label.image = new_canvas
        self._applied_effects.append(effect["name"])
        self._log(f"[{effect['id']}] {effect['name']} – done.", "ok")
        self.progress_bar.configure(value=0)
        self._set_ui_busy(False)

    def _on_effect_error(self, effect, exc):
        self._log(f"[{effect['id']}] {effect['name']} – error: {exc}", "err")
        self.progress_bar.configure(value=0)
        self._set_ui_busy(False)

    def _progress(self, value):
        """Thread-safe progress bar update — always routes through the event loop."""
        self.root.after(0, lambda v=value: self.progress_bar.configure(value=v))

    def _set_ui_busy(self, busy):
        self._effect_running = busy

    # ------------------------------------------------------------------
    # Effect implementations
    # ------------------------------------------------------------------

    def _posterize_1bit(self):
        threshold = 140
        arr = np.array(self.current_image)
        rgb = arr[..., :3].astype(np.float32)
        luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        arr[luma < threshold, :3] = 0
        arr[luma >= threshold, :3] = 255
        self.current_image = Image.fromarray(arr)
        self._progress(100)

    def _posterize_3bit(self):
        def _step(i):
            return 255 / 7 * i
        arr = np.array(self.current_image)
        rgb = arr[..., :3].astype(np.float32)
        luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        steps = [_step(i) for i in range(8)]
        arr[luma <= steps[0], :3] = steps[0]
        arr[(luma > steps[0]) & (luma <= steps[1]), :3] = steps[1]
        arr[(luma > steps[1]) & (luma <= steps[2]), :3] = steps[2]
        arr[(luma > steps[2]) & (luma <= steps[3]), :3] = steps[3]
        arr[(luma > steps[3]) & (luma <= steps[4]), :3] = steps[4]
        arr[(luma > steps[4]) & (luma <= steps[5]), :3] = steps[5]
        arr[(luma > steps[5]) & (luma <= steps[6]), :3] = steps[6]
        arr[luma > steps[6], :3] = steps[7]
        self.current_image = Image.fromarray(arr)
        self._progress(100)

    def _duotone_threshold(self):
        threshold = 210
        arr = np.array(self.current_image)
        rgb = arr[..., :3].astype(np.float32)
        luma = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
        arr[luma < threshold, :3] = 0
        arr[luma >= threshold, :3] = [255, 0, 0]
        self.current_image = Image.fromarray(arr)
        self._progress(100)

    def _negative(self):
        arr = np.array(self.current_image)
        arr[..., :3] = 255 - arr[..., :3]
        self.current_image = Image.fromarray(arr)
        self._progress(100)

    def _glow(self, radius=14):
        arr = np.array(self.current_image)
        blur = Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=radius))
        blur_arr = np.array(blur)
        strength = 0.3
        glow_arr = np.clip(arr.astype(np.int16) + blur_arr.astype(np.int16) * strength, 0, 255).astype(np.uint8)
        self.current_image = Image.fromarray(glow_arr)
        self._progress(100)

    def _color_grain(self):
        _W, _H = self.current_image.size
        arr = np.array(self.current_image).astype(np.float32)
        grain = np.random.randint(0, 256, (_H, _W, 3), dtype=np.uint8).astype(np.float32)
        strength = 0.3
        arr[..., :3] = np.clip(arr[..., :3] * (1 - strength) + grain * strength, 0, 255)
        self.current_image = Image.fromarray(arr.astype(np.uint8))
        self._progress(100)

    def _hue_shift(self, amount=10):
        arr = np.array(self.current_image.convert("RGB"))
        hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV).astype(np.float32)
        hsv[..., 0] = (hsv[..., 0] + amount / 2) % 180
        result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        self.current_image = Image.fromarray(result)
        self._progress(100)

    def _brightness_up(self):
        arr = np.array(self.current_image).astype(np.float32)
        arr[..., :3] += 10
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        self.current_image = Image.fromarray(arr)
        self._progress(100)

    def _brightness_down(self):
        arr = np.array(self.current_image).astype(np.float32)
        arr[..., :3] -= 10
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        self.current_image = Image.fromarray(arr)
        self._progress(100)

    def _ripple(self, amplitude=10, wavelength=30):
        arr = np.array(self.current_image)
        _H, _W = arr.shape[:2]

        self._progress(25)
        xx, yy = np.meshgrid(np.arange(_W), np.arange(_H))

        self._progress(50)
        src_x = np.clip(xx + (amplitude * np.sin(2 * np.pi * yy / wavelength)).astype(np.int32), 0, _W - 1)
        src_y = np.clip(yy + (amplitude * np.sin(2 * np.pi * xx / wavelength)).astype(np.int32), 0, _H - 1)

        self._progress(75)
        self.current_image = Image.fromarray(arr[src_y, src_x])
        self._progress(100)

    def _chaos(self):
        arr = np.array(self.current_image).astype(np.float32)
        _H, _W = arr.shape[:2]

        # swirl the entire image like a black hole
        self._progress(15)
        cy, cx = _H / 2, _W / 2
        y_coords, x_coords = np.mgrid[0:_H, 0:_W].astype(np.float32)
        dy = y_coords - cy
        dx = x_coords - cx
        dist = np.sqrt(dx**2 + dy**2) + 0.001
        angle = np.arctan2(dy, dx) + (800 / (dist + 1))
        src_x = np.clip((cx + dist * np.cos(angle)).astype(np.int32), 0, _W - 1)
        src_y = np.clip((cy + dist * np.sin(angle)).astype(np.int32), 0, _H - 1)
        arr = arr[src_y, src_x]

        # rgb channel split with opposing ripples
        self._progress(30)
        shift = 30
        r = np.roll(arr[..., 0], shift, axis=1)
        g = np.roll(arr[..., 1], -shift, axis=0)
        b = np.roll(arr[..., 2], shift * 2, axis=1)
        arr[..., 0] = r
        arr[..., 1] = g
        arr[..., 2] = b

        # sine ripple on top of the swirl
        self._progress(45)
        xx, yy = np.meshgrid(np.arange(_W), np.arange(_H))
        src_x2 = np.clip(xx + (25 * np.sin(2 * np.pi * yy / 40)).astype(np.int32), 0, _W - 1)
        src_y2 = np.clip(yy + (25 * np.sin(2 * np.pi * xx / 40)).astype(np.int32), 0, _H - 1)
        arr = arr[src_y2, src_x2]

        # invert only the green channel for that cursed look
        self._progress(60)
        arr[..., 1] = 255 - arr[..., 1]

        # blast random color grain over everything
        self._progress(75)
        grain = np.random.randint(0, 256, (_H, _W, 3), dtype=np.uint8).astype(np.float32)
        arr[..., :3] = np.clip(arr[..., :3] * 0.75 + grain * 0.25, 0, 255)

        # posterize to 3 levels to make it look absolutely cooked
        self._progress(90)
        arr = np.clip(arr, 0, 255)
        arr[..., :3] = (arr[..., :3] // 85) * 85
        self.current_image = Image.fromarray(arr.astype(np.uint8))
        self._progress(100)

    def _gate_of_azrael(self):
        arr = np.array(self.current_image).astype(np.float32)
        _H, _W = arr.shape[:2]
        cy, cx = _H / 2, _W / 2

        # PASS 1: polar inversion — fold space inside out
        y_coords, x_coords = np.mgrid[0:_H, 0:_W].astype(np.float32)
        dy = y_coords - cy
        dx = x_coords - cx
        dist = np.sqrt(dx**2 + dy**2) + 0.001
        max_dist = np.sqrt(cx**2 + cy**2)
        inv_dist = np.clip(max_dist**2 / (dist + 1), 0, max_dist)
        angle = np.arctan2(dy, dx)
        src_x = np.clip((cx + inv_dist * np.cos(angle)).astype(np.int32), 0, _W - 1)
        src_y = np.clip((cy + inv_dist * np.sin(angle)).astype(np.int32), 0, _H - 1)
        arr = arr[src_y, src_x]
        self._progress(12)

        # PASS 2: 3 layered vortexes at different strengths pulling in opposite directions
        for vortex_strength, vortex_cx, vortex_cy in [
            (600,  cx,        cy),
            (-400, cx * 0.3,  cy * 0.3),
            (300,  cx * 1.7,  cy * 1.7),
        ]:
            y_coords, x_coords = np.mgrid[0:_H, 0:_W].astype(np.float32)
            dy = y_coords - vortex_cy
            dx = x_coords - vortex_cx
            dist = np.sqrt(dx**2 + dy**2) + 0.001
            angle = np.arctan2(dy, dx) + (vortex_strength / (dist + 1))
            src_x = np.clip((vortex_cx + dist * np.cos(angle)).astype(np.int32), 0, _W - 1)
            src_y = np.clip((vortex_cy + dist * np.sin(angle)).astype(np.int32), 0, _H - 1)
            arr = arr[src_y, src_x]
        self._progress(30)

        # PASS 3: per-channel chromatic tear — each color lives in a different dimension
        offsets = [(0, 40, 0), (1, -30, 20), (2, 15, -45)]
        for ch, ox, oy in offsets:
            arr[..., ch] = np.roll(arr[..., ch], ox, axis=1)
            arr[..., ch] = np.roll(arr[..., ch], oy, axis=0)
        self._progress(42)

        # PASS 4: sine ripple but layered at 3 different frequencies simultaneously
        xx, yy = np.meshgrid(np.arange(_W), np.arange(_H))
        dx_total = np.zeros((_H, _W), dtype=np.float32)
        dy_total = np.zeros((_H, _W), dtype=np.float32)
        for amp, wl in [(35, 30), (15, 70), (50, 12)]:
            dx_total += amp * np.sin(2 * np.pi * yy / wl)
            dy_total += amp * np.sin(2 * np.pi * xx / wl)
        src_x2 = np.clip((xx + dx_total).astype(np.int32), 0, _W - 1)
        src_y2 = np.clip((yy + dy_total).astype(np.int32), 0, _H - 1)
        arr = arr[src_y2, src_x2]
        self._progress(57)

        # PASS 5: luma-driven hue hallucination — dark pixels go one dimension, bright go another
        arr_uint8 = np.clip(arr, 0, 255).astype(np.uint8)
        hsv = cv2.cvtColor(arr_uint8[..., :3], cv2.COLOR_RGB2HSV).astype(np.float32)
        luma = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
        hsv[..., 0] = (hsv[..., 0] + luma * 0.9) % 180
        hsv[..., 1] = np.clip(hsv[..., 1] * 2.5, 0, 255)
        arr[..., :3] = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)
        self._progress(70)

        # PASS 6: feedback echo — blend the warped image against a rolled version of itself
        echo = np.roll(arr, 18, axis=0)
        echo = np.roll(echo, -18, axis=1)
        arr = np.clip(arr * 0.6 + echo * 0.4, 0, 255)
        self._progress(82)

        # PASS 7: the void claims the shadows — anything dark enough becomes pure black abyss
        luma2 = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
        arr[luma2 < 30] = [0, 0, 0, 255] if arr.shape[2] == 4 else [0, 0, 0]

        # PASS 8: fractal posterize — 5 levels but mapped to pure electric colors
        palette = np.array([
            [0,   0,   0  ],
            [255, 0,   80 ],
            [0,   255, 180],
            [80,  0,   255],
            [255, 220, 0  ],
        ], dtype=np.float32)
        luma3 = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
        idx = np.clip((luma3 / 255 * 4).astype(np.int32), 0, 4)
        arr[..., :3] = palette[idx]
        self._progress(94)

        self.current_image = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        self._progress(100)

    def _life_is_worth_living(self):
        arr = np.array(self.current_image).astype(np.float32)
        _H, _W = arr.shape[:2]

        # soft warm glow base
        blur = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=8))
        blur_arr = np.array(blur).astype(np.float32)
        arr = np.clip(arr * 0.85 + blur_arr * 0.3, 0, 255)
        self._progress(25)

        # scatter little star sparkles randomly
        num_stars = 120
        star_x = np.random.randint(2, _W - 2, num_stars)
        star_y = np.random.randint(2, _H - 2, num_stars)
        star_colors = [
            [255, 255, 220],  # warm white
            [255, 220, 255],  # soft pink
            [220, 240, 255],  # ice blue
            [255, 255, 180],  # golden
        ]
        for i in range(num_stars):
            sx, sy = star_x[i], star_y[i]
            color = star_colors[np.random.randint(0, len(star_colors))]
            brightness = np.random.uniform(0.6, 1.0)
            c = [v * brightness for v in color]
            arr[sy, sx, :3] = np.clip(c, 0, 255)
            arr[sy - 1, sx, :3] = np.clip([v * 0.7 for v in c], 0, 255)
            arr[sy + 1, sx, :3] = np.clip([v * 0.7 for v in c], 0, 255)
            arr[sy, sx - 1, :3] = np.clip([v * 0.7 for v in c], 0, 255)
            arr[sy, sx + 1, :3] = np.clip([v * 0.7 for v in c], 0, 255)
            arr[sy - 2, sx, :3] = np.clip([v * 0.3 for v in c], 0, 255)
            arr[sy + 2, sx, :3] = np.clip([v * 0.3 for v in c], 0, 255)
            arr[sy, sx - 2, :3] = np.clip([v * 0.3 for v in c], 0, 255)
            arr[sy, sx + 2, :3] = np.clip([v * 0.3 for v in c], 0, 255)
        self._progress(70)

        # tiny second pass of extra glow so the stars feel soft and dreamy
        result_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        glow = result_img.filter(ImageFilter.GaussianBlur(radius=2))
        glow_arr = np.array(glow).astype(np.float32)
        arr = np.clip(arr * 0.9 + glow_arr * 0.2, 0, 255)
        self._progress(90)

        self.current_image = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        self._progress(100)
