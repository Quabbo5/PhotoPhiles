from tkinter import *
from tkinter import ttk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import xml.etree.ElementTree as ET
import re
import platform as _platform
from community import CommunityClient

_OS = _platform.system()   # "Darwin" | "Windows" | "Linux"


from nav_mixin       import NavMixin
from effects_mixin   import EffectsMixin
from wiki_mixin      import WikiMixin
from community_mixin import CommunityMixin
from profile_mixin   import ProfileMixin
from workspace_mixin import WorkspaceMixin
from effect_registry import load_effects


class App(NavMixin, WikiMixin, EffectsMixin, CommunityMixin, ProfileMixin, WorkspaceMixin):
    def __init__(self):

        self.root = Tk()
        self.root.title("PhotoPhile")
        # macos safespace = 1054x1020
        # windwos safespace = 1080x1020
        self.root.geometry("900x900")
        self.root.minsize(900, 900)
        #self.root.state("zoomed")
        self.root.config(bg="black")

        # dark scrollbar for all ttk widgets (clam theme allows color overrides on macOS)
        _style = ttk.Style()
        try:
            _style.theme_use("clam")
        except Exception:
            pass
        _style.configure("Vertical.TScrollbar",
                         background="#1a1a1a", troughcolor="#0a0a0a",
                         bordercolor="#000000", arrowcolor="#555555",
                         relief="flat")
        _style.configure("dark.Horizontal.TProgressbar",
                         troughcolor="#1a1a1a", background="#555555",
                         bordercolor="#000000", darkcolor="#555555",
                         lightcolor="#555555", relief="flat")

        # dunkle Titelleiste (Windows 10/11)
        # self.root.update()
        # hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        # ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int))

        # build menu
        self.menu_bar = Menu(self.root)
        self.root.config(menu=self.menu_bar)

        self.file_menu = Menu(self.menu_bar)
        self.help_menu = Menu(self.menu_bar)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

        self.file_menu.add_command(label="Open")
        self.file_menu.add_command(label="Save")
        self.file_menu.add_command(label="Save As")
        self.file_menu.add_separator()

        self.help_menu.add_command(label="Open Documentation")

        self.current_image = None
        self._original_image = None  # last freshly-loaded image (pre-effects)
        self._nav_stack   = []       # browser-style back history
        self._current_view = None    # callable that rebuilds the current panel

        # build command box (packed first so it anchors to bottom)
        self.cmd_box = Frame(self.root, bg="#141414", height=175)
        self.cmd_box.pack(side=BOTTOM, fill=X)
        self.cmd_box.pack_propagate(False)

        self.cmd_top_border = Frame(self.cmd_box, bg="#444444", height=1)
        self.cmd_top_border.pack(side=TOP, fill=X)

        self.cmd_entry_frame = Frame(self.cmd_box, bg="#1E1E1E", height=32)
        self.cmd_entry_frame.pack(side=BOTTOM, fill=X)
        self.cmd_entry_frame.pack_propagate(False)

        self.cmd_entry_border = Frame(self.cmd_box, bg="#333333", height=1)
        self.cmd_entry_border.pack(side=BOTTOM, fill=X)

        self._icon_nav = self._load_svg_icon("img/icons/nav-arrow-right.svg", display=16)
        self.cmd_prompt_label = Label(self.cmd_entry_frame, image=self._icon_nav, bg="#1E1E1E")
        self.cmd_prompt_label.pack(side=LEFT, padx=(10, 4), pady=4)

        self.cmd_entry = Entry(self.cmd_entry_frame, bg="#1E1E1E", fg="#f5f5f5", insertbackground="#f5f5f5", relief=FLAT, font="Plus_Jakarta_Sans 10", highlightthickness=0, highlightbackground="#1E1E1E", highlightcolor="#1E1E1E")
        self.cmd_entry.pack(side=LEFT, fill=X, expand=1, padx=(0, 10))

        self.log_text = Text(self.cmd_box, bg="#141414", fg="#888888", font=("Source Code Pro", 9), relief=FLAT, state=DISABLED, padx=10, pady=0, cursor="arrow", highlightthickness=0)
        self.log_text.pack(fill=BOTH, expand=1, pady=(6, 0))
        self.log_text.tag_config("info", foreground="#888888")
        self.log_text.tag_config("ok", foreground="#7EC8A4")
        self.log_text.tag_config("err", foreground="#E06C75")
        self.log_text.tag_config("prompt", foreground="#555555")

        # build toolbar
        self.toolbar = Frame(self.root, bg="#1A1A1A", height=36)
        self.toolbar.pack(side=TOP, fill=X)
        self.toolbar.pack_propagate(False)
        Frame(self.toolbar, bg="#333333", height=1).pack(side=BOTTOM, fill=X)

        _AUTH_FG     = (155, 155, 155) # same grey as all toolbar icons

        self._icon_import         = self._load_svg_icon("img/icons/folder-plus.svg")
        self._icon_save           = self._load_svg_icon("img/icons/floppy-disk.svg")
        self._icon_ws_save        = self._load_svg_icon("img/icons/floppy-disk-arrow-in.svg")
        self._icon_help           = self._load_svg_icon("img/icons/help-circle.svg")
        self._icon_random         = self._load_svg_icon("img/icons/random.svg")
        self._icon_workspace      = self._load_svg_icon("img/icons/book-stack.svg")
        self._icon_community      = self._load_svg_icon("img/icons/community.svg")
        self._icon_profile_circle = self._load_svg_icon("img/icons/profile-circle.svg")
        self._icon_login          = self._load_svg_icon("img/icons/log-in.svg",  bg=(26, 26, 26), fg=_AUTH_FG)
        self._icon_logout         = self._load_svg_icon("img/icons/log-out.svg", bg=(26, 26, 26), fg=_AUTH_FG)

        _btn = dict(bg="#1A1A1A", activebackground="#2A2A2A", relief=FLAT, bd=0, cursor="hand2", padx=6, pady=4)
        Button(self.toolbar, image=self._icon_import,    command=self._import_image,      **_btn).pack(side=LEFT)
        Button(self.toolbar, image=self._icon_random,    command=self._import_random,     **_btn).pack(side=LEFT)
        Button(self.toolbar, image=self._icon_save,      command=self._save_image,        **_btn).pack(side=LEFT)
        Button(self.toolbar, image=self._icon_ws_save,   command=self._save_to_workspace, **_btn).pack(side=LEFT)
        Button(self.toolbar, image=self._icon_help,      command=self._open_base_wiki,    **_btn).pack(side=LEFT)
        Button(self.toolbar, image=self._icon_workspace, command=self._open_workspace,    **_btn).pack(side=LEFT)

        # auth area — right side of toolbar (packed after community init below)
        self._toolbar_auth_frame = Frame(self.toolbar, bg="#1A1A1A")
        self._toolbar_auth_frame.pack(side=RIGHT, padx=(0, 8))

        self.community = CommunityClient()
        self._applied_effects: list[str] = []
        self._img_cache: dict[str, Image.Image] = {}
        self._refresh_auth_toolbar()  # url/path → PIL Image

        # build main container
        self.main = PanedWindow(self.root, orient=HORIZONTAL, bg="#2D2D2D")
        self.main.pack(fill=BOTH, expand=1)

        # build left panel
        self.left_border = Frame(self.main, highlightbackground="#444444", highlightthickness=1, bg="#2D2D2D")
        self.main.add(self.left_border)
        self.left_panel = PanedWindow(self.left_border, orient=VERTICAL, bg="#2D2D2D")
        self.left_panel.pack(fill=BOTH, expand=1)

        self.list_title = Label(self.left_panel, text="Select Effect:", font="Plus_Jakarta_Sans 8 bold", anchor="nw", width=20, bg="#2D2D2D", fg="#f5f5f5")
        self.left_panel.add(self.list_title)

        # build right panel
        self.right_border = Frame(self.main, highlightbackground="#444444", highlightthickness=1, bg="#2D2D2D")
        self.main.add(self.right_border)
        self.right_border.grid_rowconfigure(0, weight=1)
        self.right_border.grid_columnconfigure(0, weight=1)

        self.right_panel = Frame(self.right_border, bg="#2D2D2D")
        self.right_panel.grid(row=0, column=0, sticky="nsew")

        # wiki inline view — lives in same grid cell, lifted on top when active
        self.wiki_view = Frame(self.right_border, bg="#2D2D2D")
        self.wiki_view.grid(row=0, column=0, sticky="nsew")
        self._wiki_open = False

        Label(self.toolbar, text="PhotoPhile v.1.2", font="Plus_Jakarta_Sans 8 bold",
              bg="#1A1A1A", fg="#666666"
             ).place(relx=0.5, rely=0.5, anchor="center")

        # build progressbar (bottom of right panel)
        self.progress_bar_frame = Frame(self.right_panel, bg="#2D2D2D", height=6)
        self.progress_bar_frame.pack(side=BOTTOM, fill=X)

        self.progress_bar = ttk.Progressbar(self.progress_bar_frame, orient=HORIZONTAL, mode="determinate", style="dark.Horizontal.TProgressbar")
        self.progress_bar.pack(fill=X)

        # image label fills remaining space
        self.image_label = Label(self.right_panel, bg="#1B1B1B")
        self.image_label.pack(fill=BOTH, expand=1)

        # build effect list
        self.effect_list = Listbox(self.left_panel, font="Plus_Jakarta_Sans 10", bg="#2D2D2D", fg="#f5f5f5", highlightthickness=0, bd=0)
        self.left_panel.add(self.effect_list)

        self.EFFECTS = load_effects(self)

        for e in self.EFFECTS:
            self.effect_list.insert(END, f"{e['id']} – {e['name']}")

        # keybinds
        self.effect_list.bind("<Double-Button-1>", self._on_click)
        self.effect_list.bind("<Return>", self._on_click)
        self.effect_list.bind("<h>", self._on_h_press)
        self.cmd_entry.bind("<Return>", self._on_enter)

        self._log("Core ready. Type an effect ID or name and press Enter.", "info")

        self.root.after(100, self._open_base_wiki)
        self.root.mainloop()

    # --- event handlers ---

    def _on_click(self, event):
        selection = self.effect_list.curselection()
        if selection:
            index = selection[0]
            self._apply_effect(index)

    def _on_enter(self, event):
        value = self.cmd_entry.get().strip()
        # self.cmd_entry.delete(0, END) # LEAVE THIS LIKE THIS

        if not value:
            return

        if value.startswith("/"):
            self._handle_command(value)
            return

        for i, effect in enumerate(self.EFFECTS):
            if effect["id"] == value or effect["name"].lower() == value.lower():
                self._apply_effect(i)
                return

        self._log(f"Unknown effect: '{value}'", "err")

    def _handle_command(self, value):
        parts = value.split()
        cmd = parts[0]
        args = parts[1:]

        if cmd == "/r":
            if self._original_image is None:
                self._log("No image loaded yet.", "err")
                return
            self.current_image = self._original_image.copy()
            self._applied_effects.clear()
            preview = self.current_image.resize((800, 800))
            tk_img = ImageTk.PhotoImage(preview)
            self.image_label.config(image=tk_img)
            self.image_label.image = tk_img
            self._log("Reset to original.", "ok")

        elif cmd == "/clear":
            self.log_text.config(state=NORMAL)
            self.log_text.delete("1.0", END)
            self.log_text.config(state=DISABLED)

        elif cmd == "/help":
            if not args:
                self._log("Usage: /help <effect id or name>", "err")
                return
            query = " ".join(args)
            for i, effect in enumerate(self.EFFECTS):
                if effect["id"] == query or effect["name"].lower() == query.lower():
                    self._show_wiki_inline(i)
                    return
            self._log(f"No effect found for '{query}'", "err")
        elif cmd == "/search":
            if not args:
                self._log("Usage: /search <query>", "err")
                return
            query = " ".join(args)
            self._show_search_inline(query)

        elif cmd == "/window" and args == ["size"]:
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            print(f"Window size: {w}x{h}")
            self._log(f"Window size: {w}x{h}", "info")

        elif cmd[1:].isdigit():
            effect_id = cmd[1:]
            for i, effect in enumerate(self.EFFECTS):
                if effect["id"] == effect_id:
                    params = effect.get("params", [])
                    if len(args) > len(params):
                        self._log(f"Too many arguments. '{effect['name']}' takes {len(params)} param(s).", "err")
                        return
                    kwargs = {}
                    for j, p in enumerate(params):
                        if j < len(args):
                            try:
                                kwargs[p["name"]] = type(p["default"])(args[j])
                            except ValueError:
                                self._log(f"Invalid value for '{p['name']}' — expected {type(p['default']).__name__}.", "err")
                                return
                    self._apply_effect(i, **kwargs)
                    return
            self._log(f"No effect with ID {effect_id}.", "err")

        else:
            self._log(f"Unknown command: '{value}'", "err")

    def _on_h_press(self, event):
        selection = self.effect_list.curselection()
        if selection:
            index = selection[0]
            self._show_wiki_inline(index)

    # --- responsive gallery ---

    def _make_responsive_gallery(self, canvas, frame, items,
                                  image_loader,        # fn(item) -> PIL Image, runs in thread
                                  meta_rows,           # fn(item) -> list of (text, font, fg)
                                  on_click,            # fn(item, img_lbl)
                                  cache_key=None):     # fn(item) -> str, enables image cache
        """4-column gallery that reflows images when the canvas width changes."""
        import threading
        MAX_COLS = 4
        PAD = 12  # px padding per cell (padx=6 each side)

        for c in range(MAX_COLS):
            frame.columnconfigure(c, weight=1)

        def _cell_sz():
            w = canvas.winfo_width()
            if w < 10:
                w = 680
            return max((w - PAD * MAX_COLS) // MAX_COLS, 60)

        # track every image label for resize
        _img_lbls = []

        def _set_image(lbl, pil_img, sz):
            resized = pil_img.resize((sz, sz), Image.LANCZOS)
            tk_img  = ImageTk.PhotoImage(resized)
            lbl.config(image=tk_img, text="", width=sz, height=sz)
            lbl.image = tk_img

        for idx, item in enumerate(items):
            r, c = idx // MAX_COLS, idx % MAX_COLS
            cell = Frame(frame, bg="#2D2D2D", padx=4, pady=4)
            cell.grid(row=r, column=c, padx=6, pady=6, sticky="nsew")

            sz = _cell_sz()
            img_lbl = Label(cell, text="…", bg="#2D2D2D", fg="#555555",
                            width=sz // 8, height=sz // 16)
            img_lbl.pack()
            img_lbl._pil = None  # will hold PIL Image once loaded

            for text, font, fg in meta_rows(item):
                Label(cell, text=text, font=font, bg="#2D2D2D", fg=fg,
                      wraplength=sz, anchor="center").pack(fill=X)

            def _load(it=item, lbl=img_lbl):
                try:
                    key = cache_key(it) if cache_key else None
                    if key and key in self._img_cache:
                        pil = self._img_cache[key]
                    else:
                        pil = image_loader(it)
                        if key:
                            self._img_cache[key] = pil
                    lbl._pil = pil
                    s = _cell_sz()
                    lbl.after(0, lambda l=lbl, p=pil, s=s: _set_image(l, p, s))
                except Exception:
                    lbl.after(0, lambda l=lbl: l.config(text="✗"))

            threading.Thread(target=_load, daemon=True).start()
            _img_lbls.append(img_lbl)

            def _click(_, it=item, lbl=img_lbl):
                on_click(it, lbl)
            cell.bind("<Button-1>", _click)
            img_lbl.bind("<Button-1>", _click)
            img_lbl.config(cursor="hand2")

        # debounced resize
        _last_w = [0]
        _after_id = [None]

        def _on_canvas_resize(e):
            if abs(e.width - _last_w[0]) < 4:
                return
            _last_w[0] = e.width
            if _after_id[0]:
                canvas.after_cancel(_after_id[0])
            def _apply():
                sz = _cell_sz()
                for lbl in _img_lbls:
                    if lbl._pil is not None:
                        _set_image(lbl, lbl._pil, sz)
            _after_id[0] = canvas.after(120, _apply)

        canvas.bind("<Configure>", _on_canvas_resize, add="+")

    # --- label button (macOS-safe colored button) ---

    def _refresh_auth_toolbar(self):
        """Rebuild the login/logout area on the right side of the toolbar."""
        for w in self._toolbar_auth_frame.winfo_children():
            w.destroy()
        _ibtn = dict(bg="#1A1A1A", activebackground="#2A2A2A",
                     relief=FLAT, bd=0, cursor="hand2", padx=6, pady=4)
        if self.community.logged_in:
            Label(self._toolbar_auth_frame,
                  text=self.community.username or "",
                  font="Plus_Jakarta_Sans 8", bg="#1A1A1A", fg="#888888",
                  padx=4).pack(side=LEFT)
            Button(self._toolbar_auth_frame, image=self._icon_community,
                   command=self._open_community, **_ibtn).pack(side=LEFT)
            Button(self._toolbar_auth_frame, image=self._icon_profile_circle,
                   command=self._open_profile,   **_ibtn).pack(side=LEFT)
            def _logout():
                self.community.logout()
                self._refresh_auth_toolbar()
                self._log("Logged out.", "info")
                self._nav_stack.clear()
                self._wiki_open = True
                self.wiki_view.lift()
                self.root.bind("<Escape>", self._close_wiki_inline)
                self._auth_dialog()
            Button(self._toolbar_auth_frame, image=self._icon_logout,
                   command=_logout, **_ibtn).pack(side=LEFT)
        else:
            def _login():
                self._wiki_open = True
                self.wiki_view.lift()
                self.root.bind("<Escape>", self._close_wiki_inline)
                self._auth_dialog()
            Button(self._toolbar_auth_frame, image=self._icon_login,
                   command=_login, **_ibtn).pack(side=LEFT)

    def _btn(self, parent, text, command, bg="#111111", fg="#f5f5f5",
             font="Plus_Jakarta_Sans 9 bold", padx=14, pady=7, image=None,
             outline=None):
        """Label-based button that respects bg/fg on macOS."""
        kwargs = dict(bg=bg, fg=fg, font=font, padx=padx, pady=pady, cursor="hand2")
        if image is not None:
            kwargs["image"]    = image
            kwargs["compound"] = LEFT if text else "image"
        if outline:
            kwargs["highlightthickness"]  = 1
            kwargs["highlightbackground"] = bg      # invisible until hover
            kwargs["highlightcolor"]      = bg
        lbl = Label(parent, text=text, **kwargs)
        if bg == "#221F3A":
            hover = "#2A2A4A"
        elif bg == "#424242":
            hover = "#505050"
        elif bg == "#555555":
            hover = "#666666"
        else:
            hover = "#222222"

        def _enter(_):
            lbl.config(bg=hover)
            if outline:
                lbl.config(highlightbackground=outline, highlightcolor=outline)
        def _leave(_):
            lbl.config(bg=bg)
            if outline:
                lbl.config(highlightbackground=bg, highlightcolor=bg)

        lbl.bind("<Enter>", _enter)
        lbl.bind("<Leave>", _leave)
        lbl.bind("<ButtonPress-1>",   lambda _: lbl.config(bg="#333333"))
        lbl.bind("<ButtonRelease-1>", lambda _: (lbl.config(bg=hover), command()))
        return lbl

    def _bind_scroll(self, canvas):
        """Attach trackpad/mouse + arrow key scrolling to a Canvas (cross-platform).

        Uses a single root-level handler so scroll works regardless of which child
        widget is under the cursor.  _active_scroll_canvas is updated on every call
        so navigating to a new view instantly redirects scroll there.
        """
        self._active_scroll_canvas = canvas

        if not getattr(self, '_scroll_handler_bound', False):
            def _global_scroll(e):
                c = getattr(self, '_active_scroll_canvas', None)
                if c is None:
                    return
                try:
                    if not c.winfo_exists():
                        self._active_scroll_canvas = None
                        return
                    # Guard: don't scroll when all content already fits in the viewport
                    lo, hi = c.yview()
                    if lo <= 0.0 and hi >= 1.0:
                        return
                except Exception:
                    self._active_scroll_canvas = None
                    return
                if _OS == "Windows":
                    step = int(-e.delta / 120) * 2
                else:
                    # Scale + cap: delta can be hundreds on fast macOS swipes
                    step = max(-4, min(4, int(-e.delta / 30)))
                    if step == 0:
                        step = -1 if e.delta > 0 else 1
                c.yview_scroll(step, "units")

            self.root.bind_all("<MouseWheel>", _global_scroll)

            if _OS == "Linux":
                def _linux_up(_):
                    c = getattr(self, '_active_scroll_canvas', None)
                    if c:
                        c.yview_scroll(-1, "units")
                def _linux_down(_):
                    c = getattr(self, '_active_scroll_canvas', None)
                    if c:
                        c.yview_scroll(1, "units")
                self.root.bind_all("<Button-4>", _linux_up)
                self.root.bind_all("<Button-5>", _linux_down)

            self._scroll_handler_bound = True

        canvas.bind("<Up>",    lambda _: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Down>",  lambda _: canvas.yview_scroll( 1, "units"))
        canvas.bind("<Prior>", lambda _: canvas.yview_scroll(-5, "units"))
        canvas.bind("<Next>",  lambda _: canvas.yview_scroll( 5, "units"))
        canvas.focus_set()

    # --- logging ---

    def _log(self, message, tag="info"):
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, f"  {message}\n", tag)
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)

    # --- core ---

    def _resize(self, path):
        img = Image.open(path)
        _W, _H = img.size
        if _W == _H:
            return img
        elif _W > _H:
            cut = round((_W - _H) // 2)
            return img.crop((cut, 0, _W - cut, _H))
        else:
            cut = round((_H - _W) // 2)
            return img.crop((0, cut, _W, _H - cut))

    # --- toolbar ---

    def _load_svg_icon(self, path, display=22, bg=(26, 26, 26), fg=(155, 155, 155)):
        sc  = 6
        s   = display * sc
        lw  = round(sc * 1.4)

        tree = ET.parse(path)
        root = tree.getroot()
        vb   = root.get("viewBox", "0 0 24 24").split()
        vw, vh = float(vb[2]), float(vb[3])
        sx, sy = s / vw, s / vh

        img = Image.new("RGB", (s, s), bg)
        d   = ImageDraw.Draw(img)

        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "path":
                segs = self._parse_svg_path(elem.get("d", ""), sx, sy)
                for seg in segs:
                    if len(seg) >= 2:
                        d.line(seg, fill=fg, width=lw)

        img = img.resize((display, display), Image.LANCZOS)
        return ImageTk.PhotoImage(img)

    def _parse_svg_path(self, data, sx, sy):
        segments, cur, cx, cy, start_x, start_y = [], [], 0.0, 0.0, 0.0, 0.0
        tokens = re.findall(r"[MmLlCcZzHhVvSs]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", data)
        i, cmd = 0, None

        def bezier(p0, p1, p2, p3, steps=16):
            pts = []
            for k in range(steps + 1):
                t = k / steps
                u = 1 - t
                x = u**3*p0[0] + 3*u**2*t*p1[0] + 3*u*t**2*p2[0] + t**3*p3[0]
                y = u**3*p0[1] + 3*u**2*t*p1[1] + 3*u*t**2*p2[1] + t**3*p3[1]
                pts.append((x * sx, y * sy))
            return pts

        while i < len(tokens):
            t = tokens[i]
            if t.isalpha():
                cmd = t; i += 1; continue
            try:
                if cmd in "Mm":
                    x, y = float(tokens[i]), float(tokens[i+1]); i += 2
                    if cmd == "m": x += cx; y += cy
                    if cur: segments.append(cur)
                    start_x, start_y, cx, cy = x, y, x, y
                    cur = [(x*sx, y*sy)]
                    cmd = "L" if cmd == "M" else "l"
                elif cmd in "Ll":
                    x, y = float(tokens[i]), float(tokens[i+1]); i += 2
                    if cmd == "l": x += cx; y += cy
                    cur.append((x*sx, y*sy)); cx, cy = x, y
                elif cmd in "Hh":
                    x = float(tokens[i]); i += 1
                    if cmd == "h": x += cx
                    cur.append((x*sx, cy*sy)); cx = x
                elif cmd in "Vv":
                    y = float(tokens[i]); i += 1
                    if cmd == "v": y += cy
                    cur.append((cx*sx, y*sy)); cy = y
                elif cmd in "Cc":
                    x1,y1 = float(tokens[i]),float(tokens[i+1]); i+=2
                    x2,y2 = float(tokens[i]),float(tokens[i+1]); i+=2
                    x, y  = float(tokens[i]),float(tokens[i+1]); i+=2
                    if cmd == "c":
                        x1+=cx; y1+=cy; x2+=cx; y2+=cy; x+=cx; y+=cy
                    pts = bezier((cx,cy),(x1,y1),(x2,y2),(x,y))
                    cur.extend(pts[1:]);  cx, cy = x, y
                elif cmd in "Ss":
                    x2,y2 = float(tokens[i]),float(tokens[i+1]); i+=2
                    x, y  = float(tokens[i]),float(tokens[i+1]); i+=2
                    if cmd == "s": x2+=cx; y2+=cy; x+=cx; y+=cy
                    x1,y1 = 2*cx - x2, 2*cy - y2
                    pts = bezier((cx,cy),(x1,y1),(x2,y2),(x,y))
                    cur.extend(pts[1:]); cx, cy = x, y
                elif cmd in "Zz":
                    cur.append((start_x*sx, start_y*sy))
                    segments.append(cur); cur = []; cmd = None
                else:
                    i += 1
            except (IndexError, ValueError):
                i += 1

        if cur:
            segments.append(cur)
        return segments

    def _import_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp")])
        if not path:
            return
        self.current_image = self._resize(path)
        self._original_image = self.current_image.copy()
        self._applied_effects.clear()
        new_img = self.current_image.resize((800, 800))
        new_canvas = ImageTk.PhotoImage(new_img)
        self.image_label.config(image=new_canvas)
        self.image_label.image = new_canvas
        self._log(f"Imported: {path.split('/')[-1]}", "ok")

    def _import_random(self):
        import threading, urllib.request, io as _io
        self._log("Fetching random image…", "info")

        def _fetch():
            try:
                url = "https://picsum.photos/1600/1600"
                req = urllib.request.Request(url, headers={"User-Agent": "Bogoshop/1.0"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    data = r.read()
                img = Image.open(_io.BytesIO(data)).convert("RGBA")
                self.current_image = img
                self._original_image = img.copy()
                self._applied_effects.clear()
                preview = img.resize((800, 800))
                tk_img = ImageTk.PhotoImage(preview)
                def _update():
                    self.image_label.config(image=tk_img)
                    self.image_label.image = tk_img
                    if self._wiki_open:
                        self._close_wiki_inline()
                    self._log("Random image loaded from Picsum.", "ok")
                self.root.after(0, _update)
            except Exception as e:
                self.root.after(0, lambda: self._log(f"Picsum error: {e}", "err"))

        threading.Thread(target=_fetch, daemon=True).start()

    def _save_image(self):
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("All files", "*.*")])
        if not path:
            return
        self.current_image.save(path)
        self._log(f"Saved: {path.split('/')[-1]}", "ok")

    def _load_wiki(self, index):
        file_path = "img/pngs/waves.png"

        def _generate_preview():
            original = self.current_image.copy()

            self.current_image = Image.open(file_path).convert("RGBA")
            self.EFFECTS[index]["fn"]()
            preview = self.current_image.copy()
            self.current_image = original
            preview = preview.resize((350, 220))
            return ImageTk.PhotoImage(preview)

        wiki = Toplevel()
        wiki.geometry("800x900")
        wiki.minsize(800,900)
        wiki.title(f"Wiki for: {self.EFFECTS[index]['name']}")

        img_before = Image.open(file_path).convert("RGBA")
        img_before = img_before.resize((350, 220))
        img_before_resized = ImageTk.PhotoImage(img_before)

        img_after_resized = _generate_preview()

        Label(wiki, justify=LEFT, padx=0, pady=0, anchor=None,
                    text=self.EFFECTS[index]["name"], fg="#f5f5f5", bg="#221F3A",
                    font="Helvetica 24 bold", height=2
              ).pack(side=TOP, anchor="nw", fill=X)

        Label(wiki, justify=LEFT, padx=0, pady=0, anchor=None,
                    text=f"ID: #{self.EFFECTS[index]['id']}", fg="#c0c0c0", bg="#424242",
                    font="Helvetica 13 bold", height=1
              ).pack(side=TOP, anchor="nw", fill=X)

        Label(wiki, justify=LEFT, padx=0, pady=0, anchor=None,
                    text=f"Author: {self.EFFECTS[index]['author']}",
                    fg="#808080", bg="#424242", font="Helvetica 9 italic", height=1
              ).pack(side=TOP, anchor="nw", fill=X)

        image_frame = Frame(wiki, bg="#4D4D4D")
        image_frame.pack(fill=X)

        # Before
        before_frame = Frame(image_frame, bg="#4D4D4D")
        before_frame.pack(side=LEFT, padx=10, pady=10)

        before_label = Label(before_frame, image=img_before_resized)
        before_label.image = img_before_resized
        before_label.pack()

        Label(before_frame, text="Before",
                fg="#808080", bg="#4D4D4D",
                font="Helvetica 12 italic", height=1
             ).pack()

        # After
        after_frame = Frame(image_frame, bg="#4D4D4D")
        after_frame.pack(side=RIGHT, padx=10, pady=10)

        after_label = Label(after_frame, image=img_after_resized)
        after_label.image = img_after_resized
        after_label.pack()

        Label(after_frame, text="After",
                fg="#808080", bg="#4D4D4D",
                font="Helvetica 12 italic", height=1
             ).pack()

        with open(f"wiki/{self.EFFECTS[index]['id']}.md", "r") as f:
            raw_text = f.read()

        wiki_text = Text(wiki, bg="#2D2D2D", relief=FLAT, padx=10, pady=10)
        wiki_text.pack(fill=BOTH, expand=1)
        self._render_markdown(wiki_text, raw_text)

        wiki.mainloop()


if __name__ == "__main__":
    app = App()
