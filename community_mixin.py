from tkinter import *
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import threading
import io


class CommunityMixin:

    def _open_community(self):
        self._nav_stack.clear()
        if not self.community.logged_in:
            self._auth_dialog()
        else:
            self._show_community_panel()

    def _auth_dialog(self, start_mode="login"):
        for w in self.wiki_view.winfo_children():
            w.destroy()

        BG   = "#2d2d2d"
        CARD = "#424242"
        BLUE = "#231f3a"

        # banner
        hdr = Frame(self.wiki_view, bg=BLUE)
        hdr.pack(fill=X)
        Label(hdr, text="Community", font="Plus_Jakarta_Sans 14 bold",
              bg=BLUE, fg="#f5f5f5", padx=14, pady=8).pack(side=LEFT)
        Frame(self.wiki_view, bg="#333333", height=1).pack(fill=X)

        # centered card
        outer = Frame(self.wiki_view, bg=BG)
        outer.pack(fill=BOTH, expand=1)
        card = Frame(outer, bg=CARD, padx=2, pady=2)
        card.place(relx=0.5, rely=0.5, anchor="center")

        _lbl = dict(bg=CARD, fg="#7070A0", font="Plus_Jakarta_Sans 8 bold", anchor="w")
        _ent = dict(bg="#333333", fg="#f5f5f5", insertbackground="#f5f5f5",
                    relief=FLAT, font="Plus_Jakarta_Sans 10",
                    highlightthickness=1, highlightbackground="#3a3a3a",
                    highlightcolor="#231f3a", width=30)

        mode = [start_mode]  # mutable so inner functions can update it

        # persistent status label — sits outside the rebuilding form area
        status = Label(card, text="", font="Plus_Jakarta_Sans 8",
                       bg=CARD, fg="#E06C75", wraplength=300)

        form_area = Frame(card, bg=CARD)
        form_area.pack(padx=36, pady=(10, 0), fill=X)

        def _build_form():
            for w in form_area.winfo_children():
                w.destroy()
            status.config(text="")

            is_login = mode[0] == "login"

            # ── heading ───────────────────────────────────────────────────
            Label(form_area,
                  text="Login" if is_login else "Create account",
                  font="Plus_Jakarta_Sans 16 bold", bg=CARD, fg="#f5f5f5",
                  anchor="w").pack(fill=X, pady=(14, 16))

            Frame(form_area, bg="#555555", height=1).pack(fill=X, pady=(0, 14))

            # ── username (signup only) ────────────────────────────────────
            user_entry = None
            if not is_login:
                Label(form_area, text="USERNAME", **_lbl).pack(fill=X)
                user_entry = Entry(form_area, **_ent)
                user_entry.pack(fill=X, ipady=6, pady=(3, 12))

            # ── email ─────────────────────────────────────────────────────
            Label(form_area, text="EMAIL", **_lbl).pack(fill=X)
            email_entry = Entry(form_area, **_ent)
            email_entry.pack(fill=X, ipady=6, pady=(3, 12))

            # ── password ──────────────────────────────────────────────────
            Label(form_area, text="PASSWORD", **_lbl).pack(fill=X)
            pass_entry = Entry(form_area, show="•", **_ent)
            pass_entry.pack(fill=X, ipady=6, pady=(3, 2))

            if is_login:
                Label(form_area, text="Forgot password?",
                      font="Plus_Jakarta_Sans 7", bg=CARD, fg="#555577",
                      anchor="w", cursor="hand2").pack(anchor="w", pady=(0, 4))

            # ── status ────────────────────────────────────────────────────
            status.pack(pady=(6, 0), padx=0, anchor="w")

            # ── main action button ────────────────────────────────────────
            def _attempt():
                email    = email_entry.get().strip()
                password = pass_entry.get()
                if is_login:
                    if not email or not password:
                        status.config(text="Please enter your email and password.")
                        return
                    err = self.community.login(email, password)
                else:
                    uname = (user_entry.get().strip() if user_entry else "")
                    if not uname or not email or not password:
                        status.config(text="Please fill in all fields.")
                        return
                    err = self.community.register(email, password, uname)
                if err:
                    status.config(text=err)
                else:
                    self._log(f"Logged in as {self.community.username}", "ok")
                    self._refresh_auth_toolbar()
                    self._show_community_panel()

            self._btn(form_area,
                      "Log In" if is_login else "Create Account",
                      _attempt,
                      bg="#555555", fg="#f5f5f5",
                      font="Plus_Jakarta_Sans 9 bold",
                      padx=0, pady=7).pack(fill=X, pady=(10, 0))

            # ── mode switcher ─────────────────────────────────────────────
            sw_row = Frame(form_area, bg=CARD)
            sw_row.pack(pady=(14, 20))
            if is_login:
                Label(sw_row, text="Don't have an account? ",
                      font="Plus_Jakarta_Sans 8", bg=CARD, fg="#666666").pack(side=LEFT)
                sw = Label(sw_row, text="Sign up",
                           font="Plus_Jakarta_Sans 8 bold", bg=CARD, fg="#9A9AFF",
                           cursor="hand2")
            else:
                Label(sw_row, text="Already have an account? ",
                      font="Plus_Jakarta_Sans 8", bg=CARD, fg="#666666").pack(side=LEFT)
                sw = Label(sw_row, text="Log in",
                           font="Plus_Jakarta_Sans 8 bold", bg=CARD, fg="#9A9AFF",
                           cursor="hand2")
            sw.pack(side=LEFT)
            sw.bind("<Enter>", lambda _: sw.config(fg="#ccccff"))
            sw.bind("<Leave>", lambda _: sw.config(fg="#9A9AFF"))

            def _switch(_):
                mode[0] = "signup" if is_login else "login"
                self.root.after(0, _build_form)

            sw.bind("<Button-1>", _switch)

            # bind Return key and focus first field
            self.wiki_view.bind("<Return>", lambda _: _attempt())
            (user_entry or email_entry).focus_set()

        _build_form()

        self._wiki_open = True
        self.wiki_view.lift()
        self.root.bind("<Escape>", self._close_wiki_inline)

    def _show_community_panel(self):
        self._nav_push()
        self._current_view = lambda: self._show_community_panel()
        for widget in self.wiki_view.winfo_children():
            widget.destroy()

        # header
        hdr = Frame(self.wiki_view, bg="#221F3A")
        hdr.pack(fill=X)
        Label(hdr, text="Community", font="Plus_Jakarta_Sans 14 bold",
              bg="#221F3A", fg="#f5f5f5", padx=14, pady=8).pack(side=LEFT)
        Label(hdr, text=f"logged in as  {self.community.username}",
              font="Plus_Jakarta_Sans 8 italic",
              bg="#221F3A", fg="#888888").pack(side=RIGHT, padx=14)

        Frame(self.wiki_view, bg="#333333", height=1).pack(fill=X)

        # gallery
        gallery_outer = Frame(self.wiki_view, bg="#1E1E1E")
        gallery_outer.pack(fill=BOTH, expand=1)

        canvas = Canvas(gallery_outer, bg="#1E1E1E", highlightthickness=0)
        scrollbar = Scrollbar(gallery_outer, orient=VERTICAL, command=canvas.yview,
                              bg="#1a1a1a", troughcolor="#0a0a0a",
                              activebackground="#333333", relief="flat", borderwidth=0, width=10)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=1)

        gallery = Frame(canvas, bg="#1E1E1E")
        canvas_window = canvas.create_window((0, 0), window=gallery, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(canvas_window, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        gallery.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._bind_scroll(canvas)

        self._load_gallery(canvas, gallery)

        self._wiki_open = True
        self.wiki_view.lift()
        self.root.bind("<Escape>", self._close_wiki_inline)

    def _load_gallery(self, canvas, gallery: Frame):
        import urllib.request

        posts = self.community.fetch_posts()
        if not posts:
            Label(gallery, text="No posts yet. Be the first to upload!",
                  font="Plus_Jakarta_Sans 10 italic", bg="#1E1E1E", fg="#555555"
                  ).pack(pady=40)
            return

        def _loader(post):
            url = post.get("image_url", "")
            with urllib.request.urlopen(url, timeout=8) as r:
                data = r.read()
            return Image.open(io.BytesIO(data)).convert("RGB")

        def _meta(post):
            t = post.get("title", "untitled")
            if len(t) > 22: t = t[:20] + "…"
            return [
                (t,                              "Plus_Jakarta_Sans 8 bold",   "#f5f5f5"),
                (f"by {post.get('username','?')}","Plus_Jakarta_Sans 7 italic", "#666666"),
            ]

        self._make_responsive_gallery(
            canvas, gallery, posts, _loader, _meta,
            lambda post, lbl: self._open_post_view(post, lbl),
            cache_key=lambda post: post.get("image_url", "")
        )

    def _open_post_view(self, post: dict, img_lbl):
        import urllib.request
        self._nav_push()
        self._current_view = lambda: self._open_post_view(post, img_lbl)
        for w in self.wiki_view.winfo_children():
            w.destroy()

        BG       = "#1A1A1A"
        CBGRGB   = (30, 30, 46)   # #1E1E2E — comment bg
        FG_NORM  = (90, 90, 110)
        FG_UP    = (126, 200, 164)
        FG_DOWN  = (224, 108, 117)

        # Load vote icons (outline = not voted, tagged = voted)
        _ico_up_off  = self._load_svg_icon("img/icons/upvote-arrow-up-solid.svg",
                                            display=14, bg=CBGRGB, fg=FG_NORM)
        _ico_up_on   = self._load_svg_icon("img/icons/upvote-arrow-up-solid-tagged.svg",
                                            display=14, bg=CBGRGB, fg=FG_UP)
        _ico_dn_off  = self._load_svg_icon("img/icons/upvote-arrow-down-solid.svg",
                                            display=14, bg=CBGRGB, fg=FG_NORM)
        _ico_dn_on   = self._load_svg_icon("img/icons/upvote-arrow-down-solid-tagged.svg",
                                            display=14, bg=CBGRGB, fg=FG_DOWN)

        post_id    = str(post.get("id", ""))
        # Fetch current user's votes for all comments in this post
        user_votes = self.community.get_user_comment_votes(post_id)

        # ── scrollable area ───────────────────────────────────────────────
        outer = Frame(self.wiki_view, bg=BG)
        outer.pack(fill=BOTH, expand=1)

        canvas = Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        sb = Scrollbar(outer, orient=VERTICAL, command=canvas.yview,
                       bg="#1a1a1a", troughcolor="#0a0a0a",
                       activebackground="#333333", relief="flat", borderwidth=0, width=10)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=1)

        content = Frame(canvas, bg=BG)
        _cw = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_canvas_resize(e):
            canvas.itemconfig(_cw, width=e.width)
        canvas.bind("<Configure>", _on_canvas_resize)
        content.bind("<Configure>", lambda _: canvas.configure(
            scrollregion=canvas.bbox("all")))
        self._bind_scroll(canvas)

        # ── banner header ─────────────────────────────────────────────────
        hdr = Frame(content, bg="#221F3A")
        hdr.pack(fill=X)
        self._btn(hdr, "← Back", self._nav_back,
                  bg="#221F3A", fg="#888888",
                  font="Plus_Jakarta_Sans 9", padx=12, pady=8
                  ).pack(side=LEFT)
        Label(hdr, text=post.get("title", "untitled"),
              font="Plus_Jakarta_Sans 14 bold", bg="#221F3A", fg="#f5f5f5",
              padx=8).pack(side=LEFT)

        Frame(content, bg="#333333", height=1).pack(fill=X)
        meta_row = Frame(content, bg="#2A2A2A")
        meta_row.pack(fill=X)

        # left: by <username> (clickable → profile, right-click → copy)
        _uname = post.get("username", "?")
        by_lbl = Label(meta_row, text="by ",
                       font="Plus_Jakarta_Sans 8 italic",
                       bg="#2A2A2A", fg="#888888", padx=12, pady=4)
        by_lbl.pack(side=LEFT)
        uname_lbl = Label(meta_row, text=_uname,
                          font="Plus_Jakarta_Sans 8 italic bold",
                          bg="#2A2A2A", fg="#aaaaaa", pady=4, cursor="hand2")
        uname_lbl.pack(side=LEFT)
        uname_lbl.bind("<Enter>", lambda _: uname_lbl.config(fg="#f5f5f5"))
        uname_lbl.bind("<Leave>", lambda _: uname_lbl.config(fg="#aaaaaa"))
        uname_lbl.bind("<Button-1>", lambda _, u=_uname: self._open_user_profile(u))
        uname_lbl.bind("<Button-2>", lambda _, u=_uname: (
            self.root.clipboard_clear(), self.root.clipboard_append(u),
            uname_lbl.config(fg="#7EC8A4"),
            uname_lbl.after(1200, lambda: uname_lbl.config(fg="#aaaaaa"))
        ))

        # right: Post ID: <number> (click to copy)
        _sid = str(post.get("short_id", ""))
        if _sid:
            id_frame = Frame(meta_row, bg="#2A2A2A")
            id_frame.pack(side=RIGHT, padx=8)
            Label(id_frame, text="Post ID: ",
                  font="Plus_Jakarta_Sans 8", bg="#2A2A2A", fg="#555555",
                  pady=4).pack(side=LEFT)
            sid_lbl = Label(id_frame, text=f"<{_sid}>",
                            font="Plus_Jakarta_Sans 8 bold", bg="#2A2A2A", fg="#555555",
                            cursor="hand2", pady=4)
            sid_lbl.pack(side=LEFT)
            def _copy_id(s=_sid):
                self.root.clipboard_clear()
                self.root.clipboard_append(f"<{s}>")
                sid_lbl.config(fg="#7EC8A4")
                sid_lbl.after(1200, lambda: sid_lbl.config(fg="#555555"))
            sid_lbl.bind("<Button-1>", lambda _: _copy_id())
            sid_lbl.bind("<Enter>", lambda _: sid_lbl.config(fg="#aaaaaa"))
            sid_lbl.bind("<Leave>", lambda _: sid_lbl.config(fg="#555555"))

        Frame(content, bg="#333333", height=1).pack(fill=X)

        # ── image ─────────────────────────────────────────────────────────
        img_container = Label(content, bg=BG, text="loading…",
                              fg="#444444", font="Plus_Jakarta_Sans 10")
        img_container.pack(pady=14, padx=16)

        def _load_full():
            try:
                raw = getattr(img_lbl, "_raw", None)
                if raw is None:
                    with urllib.request.urlopen(post["image_url"], timeout=10) as r:
                        raw = r.read()
                full = Image.open(io.BytesIO(raw)).convert("RGB")
                full.thumbnail((680, 680))
                tk_img = ImageTk.PhotoImage(full)
                img_container.config(image=tk_img, text="")
                img_container.image = tk_img
                img_container._raw = raw
            except Exception as e:
                img_container.config(text=f"Failed: {e}", fg="#E06C75")

        threading.Thread(target=_load_full, daemon=True).start()

        # ── description ───────────────────────────────────────────────────
        desc = post.get("description", "").strip()
        if desc:
            Frame(content, bg="#2A2A2A", height=1).pack(fill=X, padx=16)
            Label(content, text=desc,
                  font="Plus_Jakarta_Sans 10", bg=BG, fg="#aaaaaa",
                  anchor="w", padx=16, wraplength=680, justify=LEFT
                  ).pack(fill=X, pady=10)

        # ── action buttons ────────────────────────────────────────────────
        Frame(content, bg="#2A2A2A", height=1).pack(fill=X, padx=16)
        btn_row = Frame(content, bg=BG)
        btn_row.pack(fill=X, padx=16, pady=10)


        def _import():
            try:
                raw = getattr(img_container, "_raw", None)
                if raw is None:
                    with urllib.request.urlopen(post["image_url"], timeout=10) as r:
                        raw = r.read()
                self.current_image = Image.open(io.BytesIO(raw)).convert("RGBA")
                self._original_image = self.current_image.copy()
                self._applied_effects.clear()
                new_img = self.current_image.resize((800, 800))
                tk_img  = ImageTk.PhotoImage(new_img)
                self.image_label.config(image=tk_img)
                self.image_label.image = tk_img
                self._close_wiki_inline()
                self._log(f"Imported '{post.get('title')}' from community.", "ok")
            except Exception as e:
                self._log(f"Import failed: {e}", "err")

        def _download():
            path = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG", "*.jpg")],
                initialfile=f"{post.get('title', 'image')}.jpg"
            )
            if not path:
                return
            try:
                raw = getattr(img_container, "_raw", None)
                if raw is None:
                    with urllib.request.urlopen(post["image_url"], timeout=10) as r:
                        raw = r.read()
                with open(path, "wb") as f:
                    f.write(raw)
                self._log(f"Downloaded '{post.get('title')}' to {path}", "ok")
            except Exception as e:
                self._log(f"Download failed: {e}", "err")

        self._btn(btn_row, "Import to editor", _import).pack(side=LEFT, padx=(0, 8))
        self._btn(btn_row, "Download", _download).pack(side=LEFT)

        # ── likes + comments ──────────────────────────────────────────────

        def _time_ago(ts):
            import datetime
            try:
                t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                d = int((datetime.datetime.now(datetime.timezone.utc) - t).total_seconds())
                if d < 60:    return "just now"
                if d < 3600:  return f"{d//60}m ago"
                if d < 86400: return f"{d//3600}h ago"
                return f"{d//86400}d ago"
            except Exception:
                return ""

        # like bar
        Frame(content, bg="#2A2A2A", height=1).pack(fill=X)
        like_row = Frame(content, bg=BG)
        like_row.pack(fill=X, padx=16, pady=8)

        _like_state = {"count": 0, "liked": False}

        def _refresh_like():
            h = "♥" if _like_state["liked"] else "♡"
            like_lbl.config(text=f"{h}  {_like_state['count']}  {'Liked' if _like_state['liked'] else 'Like'}")

        def _toggle_like():
            if not self.community.session:
                self._log("Log in to like posts.", "err"); return
            def _do():
                try:
                    s = self.community.toggle_like(post_id)
                    _like_state["count"] = s["likes"]
                    _like_state["liked"] = s["has_liked"]
                    try: like_row.after(0, _refresh_like)
                    except Exception: pass
                except Exception as e:
                    self._log(str(e), "err")
            threading.Thread(target=_do, daemon=True).start()

        like_lbl = self._btn(like_row, "♡  0  Like", _toggle_like,
                             font="Plus_Jakarta_Sans 9", padx=12, pady=5)
        like_lbl.pack(side=LEFT)

        def _load_stats():
            s = self.community.get_post_stats(post_id)
            _like_state["count"] = s["likes"]
            _like_state["liked"] = s["has_liked"]
            try: like_row.after(0, _refresh_like)
            except Exception: pass
        threading.Thread(target=_load_stats, daemon=True).start()

        # comments header
        Frame(content, bg="#2A2A2A", height=1).pack(fill=X)
        chdr = Frame(content, bg=BG)
        chdr.pack(fill=X, padx=16, pady=(10, 4))
        comments_lbl = Label(chdr, text="Comments",
                             font="Plus_Jakarta_Sans 10 bold", bg=BG, fg="#f5f5f5")
        comments_lbl.pack(side=LEFT)
        Frame(content, bg="#2A2A2A", height=1).pack(fill=X)

        # comment input (logged-in only)
        if self.community.session:
            inp_row = Frame(content, bg=BG)
            inp_row.pack(fill=X, padx=16, pady=8)
            PLACEHOLDER = "Write a comment…"
            c_entry = Entry(inp_row, bg="#2D2D2D", fg="#555555",
                            insertbackground="#f5f5f5",
                            font="Plus_Jakarta_Sans 10", relief=FLAT,
                            highlightthickness=1, highlightbackground="#444444",
                            highlightcolor="#6C6C9A")
            c_entry.insert(0, PLACEHOLDER)
            c_entry.pack(side=LEFT, fill=X, expand=1, ipady=6, padx=(0, 8))
            c_entry.bind("<FocusIn>",  lambda _: (c_entry.delete(0, END), c_entry.config(fg="#f5f5f5"))
                         if c_entry.get() == PLACEHOLDER else None)
            c_entry.bind("<FocusOut>", lambda _: (c_entry.insert(0, PLACEHOLDER), c_entry.config(fg="#555555"))
                         if not c_entry.get().strip() else None)

            def _submit_top(pid=None):
                txt = c_entry.get().strip()
                if not txt or txt == PLACEHOLDER: return
                try:
                    self.community.add_comment(post_id, txt, pid)
                    c_entry.delete(0, END)
                    c_entry.config(fg="#555555"); c_entry.insert(0, PLACEHOLDER)
                    _reload_comments()
                except Exception as e:
                    self._log(str(e), "err")

            c_entry.bind("<Return>", lambda _: _submit_top())
            self._btn(inp_row, "Post", _submit_top,
                      font="Plus_Jakarta_Sans 9", padx=12, pady=5).pack(side=LEFT)

        # comments list
        comments_frame = Frame(content, bg=BG)
        comments_frame.pack(fill=X, padx=16, pady=(4, 24))

        if not hasattr(self, '_av_cache'):
            self._av_cache = {}   # username -> ImageTk.PhotoImage (best available)
            self._av_real  = set()  # usernames with a confirmed real photo loaded

        def _render_comment(parent, c, replies_map, depth=0, _pending=None):
            INDENT, CBORDER = 20, "#3A3A5A" if depth == 0 else "#2A2A3A"
            indent_px = min(depth, 4) * INDENT  # cap indent so deep threads don't go off-screen
            CBG = "#1E1E2E"
            cid = c["id"]

            block = Frame(parent, bg=CBG)
            block.pack(fill=X, pady=(0, 5), padx=(indent_px, 0))
            Frame(block, bg=CBORDER, width=3).pack(side=LEFT, fill=Y)

            # ── vote column (left) ─────────────────────────────────────────
            cur_vote = user_votes.get(cid, 0)
            vote_col = Frame(block, bg=CBG, width=32)
            vote_col.pack(side=LEFT, fill=Y, padx=(6, 2), pady=6)
            vote_col.pack_propagate(False)

            score = c.get("upvotes", 0) - c.get("downvotes", 0)
            score_clr = "#7EC8A4" if score > 0 else "#E06C75" if score < 0 else "#666666"

            up_lbl    = Label(vote_col, image=_ico_up_on if cur_vote == 1 else _ico_up_off,
                              bg=CBG, cursor="hand2")
            score_lbl = Label(vote_col, text=str(score), font="Plus_Jakarta_Sans 8 bold",
                              bg=CBG, fg=score_clr)
            dn_lbl    = Label(vote_col, image=_ico_dn_on if cur_vote == -1 else _ico_dn_off,
                              bg=CBG, cursor="hand2")
            up_lbl.pack()
            score_lbl.pack()
            dn_lbl.pack()

            def _do_vote(v, ul=up_lbl, dl=dn_lbl, sl=score_lbl, cv=[cur_vote], sc=[score]):
                new_v = 0 if cv[0] == v else v
                # Optimistic UI update
                ul.config(image=_ico_up_on if new_v == 1 else _ico_up_off)
                dl.config(image=_ico_dn_on if new_v == -1 else _ico_dn_off)
                delta = new_v - cv[0]
                sc[0] += delta
                nc = "#7EC8A4" if sc[0] > 0 else "#E06C75" if sc[0] < 0 else "#666666"
                sl.config(text=str(sc[0]), fg=nc)
                cv[0] = new_v
                user_votes[cid] = new_v
                def _bg():
                    try:
                        self.community.vote_comment(cid, new_v)
                    except Exception as e:
                        self._log(str(e), "err")
                threading.Thread(target=_bg, daemon=True).start()

            up_lbl.bind("<Button-1>", lambda _: _do_vote(1))
            dn_lbl.bind("<Button-1>", lambda _: _do_vote(-1))

            # ── content column (right) ─────────────────────────────────────
            inner = Frame(block, bg=CBG)
            inner.pack(side=LEFT, fill=X, expand=1, padx=(2, 8), pady=6)

            # header
            hr = Frame(inner, bg=CBG)
            hr.pack(fill=X)

            uname = c.get("username", "?")
            _av_img = self._av_cache.get(uname) or self._make_avatar_img(uname, size=22)
            if uname not in self._av_cache:
                self._av_cache[uname] = _av_img
            av_lbl = Label(hr, image=_av_img, bg=CBG, width=22, height=22, cursor="hand2")
            av_lbl.image = _av_img
            av_lbl.pack(side=LEFT, padx=(0, 5))
            av_lbl.bind("<Button-1>", lambda _, u=uname: self._open_user_profile(u))
            if _pending is not None and uname not in self._av_real:
                _pending.setdefault(uname, []).append(av_lbl)

            unl = Label(hr, text=uname,
                        font="Plus_Jakarta_Sans 9 bold", bg=CBG, fg="#9A9AFF",
                        cursor="hand2")
            unl.pack(side=LEFT)
            unl.bind("<Enter>", lambda _: unl.config(fg="#ccccff"))
            unl.bind("<Leave>", lambda _: unl.config(fg="#9A9AFF"))
            unl.bind("<Button-1>", lambda _, u=uname: self._open_user_profile(u))
            Label(hr, text=f"  ·  {_time_ago(c.get('created_at',''))}",
                  font="Plus_Jakarta_Sans 8", bg=CBG, fg="#555555").pack(side=LEFT)

            # body
            self._inline_text(inner, c.get("content", ""),
                              bg=CBG, fg="#dddddd",
                              font="Plus_Jakarta_Sans 10").pack(fill=X, pady=(2, 4))

            # actions (reply only — voting is via arrow icons)
            act = Frame(inner, bg=CBG)
            act.pack(fill=X)

            if self.community.session:
                rl = Label(act, text="reply", font="Plus_Jakarta_Sans 8",
                           bg="#1E1E2E", fg="#555555", cursor="hand2")
                rl.pack(side=LEFT)
                rl.bind("<Enter>", lambda _: rl.config(fg="#9A9AFF"))
                rl.bind("<Leave>", lambda _: rl.config(fg="#555555"))

                _reply_box_ref = [None]

                def _toggle_reply(cid=c["id"]):
                    if _reply_box_ref[0] and _reply_box_ref[0].winfo_exists():
                        _reply_box_ref[0].destroy(); _reply_box_ref[0] = None; return
                    rb = Frame(inner, bg="#1E1E2E")
                    rb.pack(fill=X, pady=(2, 2))
                    _reply_box_ref[0] = rb
                    rv = Entry(rb, bg="#252535", fg="#f5f5f5",
                               insertbackground="#f5f5f5",
                               font="Plus_Jakarta_Sans 9", relief=FLAT,
                               highlightthickness=1, highlightbackground="#444444")
                    rv.pack(side=LEFT, fill=X, expand=1, ipady=5)

                    def _post_reply(cid=cid):
                        txt = rv.get().strip()
                        if not txt: return
                        try:
                            self.community.add_comment(post_id, txt, cid)
                            rb.destroy(); _reply_box_ref[0] = None
                            _reload_comments()
                        except Exception as e:
                            self._log(str(e), "err")

                    rv.bind("<Return>", lambda _: _post_reply())
                    self._btn(rb, "Reply", _post_reply,
                              font="Plus_Jakarta_Sans 8", padx=8, pady=4
                              ).pack(side=LEFT, padx=(4, 0))
                    rv.focus_set()

                rl.bind("<Button-1>", lambda _: _toggle_reply())

            # render replies
            for rep in replies_map.get(c["id"], []):
                _render_comment(parent, rep, replies_map, depth + 1, _pending)

        def _render_all(comments):
            try:
                _saved_pos = canvas.yview()[0]
            except Exception:
                _saved_pos = None

            # Disconnect auto-scrollregion update so destroying widgets
            # doesn't shrink the scrollregion and snap the view to top
            content.unbind("<Configure>")

            for w in comments_frame.winfo_children():
                w.destroy()
            roots = [c for c in comments if not c.get("parent_id")]
            rmap  = {}
            for c in comments:
                if c.get("parent_id"):
                    rmap.setdefault(c["parent_id"], []).append(c)
            comments_lbl.config(text=f"Comments  ({len(comments)})")
            _pending = {}
            if not roots:
                Label(comments_frame, text="No comments yet. Be the first!",
                      font="Plus_Jakarta_Sans 9 italic", bg=BG, fg="#444444",
                      anchor="w").pack(fill=X, pady=8)
            else:
                for c in roots:
                    _render_comment(comments_frame, c, rmap, 0, _pending)

            # Update scrollregion once after full rebuild, then restore position
            canvas.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
            if _saved_pos is not None:
                canvas.yview_moveto(_saved_pos)

            # Rebind for future window resizes
            content.bind("<Configure>", lambda _: canvas.configure(
                scrollregion=canvas.bbox("all")))

            # Async: fetch real avatars for comment authors not yet cached
            if _pending:
                def _load_avatars(pending=_pending):
                    import urllib.request as _ur, io as _io
                    from PIL import Image as _Img
                    profiles = self.community.fetch_profiles_batch(list(pending.keys()))
                    for uname, prof in profiles.items():
                        url = prof.get("avatar_url", "")
                        if not url:
                            continue
                        try:
                            with _ur.urlopen(url, timeout=6) as r:
                                raw = r.read()
                            pil = _Img.open(_io.BytesIO(raw)).convert("RGB")
                            tk_img = self._make_avatar_img(uname, size=22, pil_img=pil)
                            self._av_cache[uname] = tk_img
                            self._av_real.add(uname)
                            for lbl in pending.get(uname, []):
                                try:
                                    lbl.after(0, lambda l=lbl, img=tk_img:
                                              (l.config(image=img), setattr(l, 'image', img)))
                                except Exception:
                                    pass
                        except Exception:
                            pass
                threading.Thread(target=_load_avatars, daemon=True).start()

        def _reload_comments():
            def _fetch():
                cs = self.community.get_comments(post_id)
                try: comments_frame.after(0, lambda: _render_all(cs))
                except Exception: pass
            threading.Thread(target=_fetch, daemon=True).start()

        _reload_comments()

        # ── effects footer ────────────────────────────────────────────────
        _fx = post.get("effects", "").strip()
        if _fx:
            Frame(content, bg="#222222", height=1).pack(fill=X, pady=(16, 0))
            Label(content, text="Effects applied:",
                  font="Plus_Jakarta_Sans 8 italic", bg="#1A1A1A", fg="#444444",
                  anchor="w", padx=16).pack(fill=X, pady=(6, 2))
            Label(content, text=_fx,
                  font="Plus_Jakarta_Sans 8 italic", bg="#1A1A1A", fg="#3A3A3A",
                  anchor="w", padx=16, justify=LEFT, wraplength=580).pack(fill=X, pady=(0, 20))

        self._wiki_open = True
        self.wiki_view.lift()
        self.root.bind("<Escape>", lambda _: self._show_community_panel())

    def _upload_post(self):
        if self.current_image is None:
            self._log("Load an image first before uploading.", "err")
            return
        self._nav_push()
        self._current_view = lambda: self._upload_post()

        for w in self.wiki_view.winfo_children():
            w.destroy()

        BG   = "#1A1A1A"
        CARD = "#242424"

        # ── banner ────────────────────────────────────────────────────────
        hdr = Frame(self.wiki_view, bg="#221F3A")
        hdr.pack(fill=X)
        self._btn(hdr, "← Back", self._nav_back,
                  bg="#221F3A", fg="#888888",
                  font="Plus_Jakarta_Sans 9", padx=12, pady=8
                  ).pack(side=LEFT)
        Label(hdr, text="Upload to Community",
              font="Plus_Jakarta_Sans 14 bold", bg="#221F3A", fg="#f5f5f5",
              padx=8).pack(side=LEFT)
        Frame(self.wiki_view, bg="#333333", height=1).pack(fill=X)

        # ── scrollable body ───────────────────────────────────────────────
        outer = Frame(self.wiki_view, bg=BG)
        outer.pack(fill=BOTH, expand=1)
        canvas = Canvas(outer, bg=BG, highlightthickness=0, bd=0)
        sb = Scrollbar(outer, orient=VERTICAL, command=canvas.yview,
                       bg="#1a1a1a", troughcolor="#0a0a0a",
                       activebackground="#333333", relief="flat", borderwidth=0, width=10)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=1)
        body = Frame(canvas, bg=BG)
        _cw = canvas.create_window((0, 0), window=body, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(_cw, width=e.width))
        body.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        self._bind_scroll(canvas)

        PAD = 28

        # ── preview card ──────────────────────────────────────────────────
        prev_card = Frame(body, bg=CARD)
        prev_card.pack(fill=X, padx=PAD, pady=(20, 0))
        thumb = self.current_image.copy().convert("RGB")
        thumb.thumbnail((320, 320))
        _tk_thumb = ImageTk.PhotoImage(thumb)
        thumb_lbl = Label(prev_card, image=_tk_thumb, bg=CARD)
        thumb_lbl.pack(pady=16)
        thumb_lbl._tk_thumb = _tk_thumb

        Frame(body, bg="#333333", height=1).pack(fill=X, padx=PAD)

        # ── form card ─────────────────────────────────────────────────────
        form = Frame(body, bg=CARD)
        form.pack(fill=X, padx=PAD, pady=(0, 24))

        _lbl = dict(bg=CARD, fg="#888888", font="Plus_Jakarta_Sans 8", anchor="w")
        _ent = dict(bg="#1E1E1E", fg="#f5f5f5", insertbackground="#f5f5f5",
                    relief=FLAT, font="Plus_Jakarta_Sans 10",
                    highlightthickness=1, highlightbackground="#444444",
                    highlightcolor="#6C6C9A")

        Label(form, text="TITLE", **_lbl).pack(fill=X, padx=16, pady=(16, 2))
        title_entry = Entry(form, **_ent)
        title_entry.pack(fill=X, padx=16, ipady=6, pady=(0, 12))

        Label(form, text="DESCRIPTION", **_lbl).pack(fill=X, padx=16, pady=(0, 2))
        desc_entry = Text(form, height=5, **_ent)
        desc_entry.pack(fill=X, padx=16, pady=(0, 16))

        Frame(form, bg="#333333", height=1).pack(fill=X, padx=0)

        status = Label(form, text="", font="Plus_Jakarta_Sans 8",
                       bg=CARD, fg="#E06C75", wraplength=500, justify=LEFT)
        status.pack(fill=X, padx=16, pady=(8, 0))

        btn_row = Frame(form, bg=CARD)
        btn_row.pack(fill=X, padx=16, pady=(8, 16))

        def _do_upload():
            title = title_entry.get().strip() or "untitled"
            desc  = desc_entry.get("1.0", END).strip()
            status.config(text="Uploading…", fg="#888888")
            body.update_idletasks()
            err = self.community.upload_post(
                self.current_image, title, self._applied_effects, desc)
            if err:
                status.config(text=err, fg="#E06C75")
            else:
                self._log(f"Uploaded '{title}' to community.", "ok")
                self._show_community_panel()

        self._btn(btn_row, "Upload", _do_upload).pack(side=LEFT, padx=(0, 8))
        self._btn(btn_row, "Cancel", self._nav_back).pack(side=LEFT)

        title_entry.focus_set()
        self.wiki_view.bind("<Return>", lambda _: _do_upload())

        self._wiki_open = True
        self.wiki_view.lift()
        self.root.bind("<Escape>", lambda _: self._show_community_panel())
