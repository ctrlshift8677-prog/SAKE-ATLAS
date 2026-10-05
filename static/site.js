/* SAKE ATLAS 互動 */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduce = matchMedia("(prefers-reduced-motion: reduce)");
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  document.documentElement.classList.add("js");
  const NAV = window.SA_NAV || {
    search: () => location.search,
    fragment: () => decodeURIComponent(location.hash.slice(1)),
    replace: (qs) => history.replaceState(null, "", qs ? `?${qs}` : location.pathname),
  };

  /* 點卡片時，只替那一張封面命名，讓換頁時封面接續到酒款頁 */
  document.addEventListener("click", (e) => {
    const a = e.target.closest("a.card");
    if (!a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
    $$(".c-cover").forEach((n) => (n.style.viewTransitionName = ""));
    const big = $(".sk-cover");
    if (big) big.style.viewTransitionName = "none";
    const c = a.querySelector(".c-cover");
    if (c) c.style.viewTransitionName = "bottle";
  });
  addEventListener("pageshow", () => $$(".c-cover").forEach((n) => (n.style.viewTransitionName = "")));

  /* 返回：站內有上一頁就退回原處（保留篩選與捲動位置），否則前往上一層 */
  const sameOriginReferrer = () => {
    try { return document.referrer && new URL(document.referrer).origin === location.origin; } catch { return false; }
  };
  const canGoBack = () => (window.SA_NAV && window.SA_NAV.canBack ? window.SA_NAV.canBack() : sameOriginReferrer() && history.length > 1);
  document.addEventListener("click", (e) => {
    const a = e.target.closest("[data-back]");
    if (!a || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
    if (canGoBack()) { e.preventDefault(); e.stopImmediatePropagation(); history.back(); }
  }, true);
  const labelBack = () => {
    const lab = $("[data-back-label]");
    if (!lab) return;
    const prev = window.SA_NAV && window.SA_NAV.prevLabel ? window.SA_NAV.prevLabel() : (sameOriginReferrer() ? "上一頁" : "");
    if (prev) lab.textContent = prev;
  };

  const icon = {
    arrow: '<svg class="ic" viewBox="0 0 256 256" aria-hidden="true"><line x1="40" y1="128" x2="216" y2="128" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/><polyline points="144 56 216 128 144 200" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="16"/></svg>',
  };
  const seal = (t, cls, tilt) => {
    const n = t.length, rows = n <= 1 ? 1 : n <= 4 ? 2 : 3, cols = Math.ceil(n / rows);
    return `<span class="seal ${cls}" style="--rows:${rows};--cols:${cols};--tilt:${tilt}deg" aria-hidden="true"><span>${esc(t)}</span></span>`;
  };

  /* 精米步合：直徑約與重量的立方根成正比，磨得越多越接近圓形 */
  const grainGeom = (p, rx0, ry0) => {
    p = Math.max(0.001, Math.min(1, p));
    const sc = Math.cbrt(p), a0 = ry0 / rx0, a = 1 + (a0 - 1) * Math.pow(p, 0.6);
    return [rx0 * sc * Math.sqrt(a0 / a), ry0 * sc * Math.sqrt(a / a0)];
  };

  function init() {
  labelBack();
  $$(".fl-tip").forEach((n) => n.remove());
  /* ───────── 酒卡：進場顯影、滑過時傾斜與光澤 ───────── */
  const cards = $$(".card");
  if (!reduce.matches && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      let k = 0;
      for (const en of entries) {
        if (!en.isIntersecting) continue;
        const c = en.target;
        io.unobserve(c);
        const d = Math.min(k++, 8) * 70;
        c.style.setProperty("--stg", `${d}ms`);
        c.classList.remove("is-pending");
        c.classList.add("is-in", "is-stamping");
        setTimeout(() => c.classList.remove("is-stamping"), 1200 + d);
      }
    }, { rootMargin: "0px 0px -6% 0px" });
    cards.forEach((c) => { if (!c.classList.contains("is-in")) { c.classList.add("is-pending"); io.observe(c); } });
  }
  if (!reduce.matches && matchMedia("(hover: hover) and (pointer: fine)").matches) {
    $$(".card .c-cover, .sk-cover.is-photo").forEach((el) => {
      let raf = 0;
      const big = el.classList.contains("sk-cover") ? 0.45 : 1;
      const move = (e) => {
        const r = el.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
        cancelAnimationFrame(raf);
        raf = requestAnimationFrame(() => {
          el.style.setProperty("--rx", `${((0.5 - y) * 9 * big).toFixed(2)}deg`);
          el.style.setProperty("--ry", `${((x - 0.5) * 11 * big).toFixed(2)}deg`);
          el.style.setProperty("--gx", `${(x * 100).toFixed(1)}%`);
          el.style.setProperty("--gy", `${(y * 100).toFixed(1)}%`);
          el.style.setProperty("--px", `${((0.5 - x) * 10).toFixed(1)}px`);
          el.style.setProperty("--py", `${((0.5 - y) * 10).toFixed(1)}px`);
        });
      };
      el.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") { el.classList.add("is-tilt"); move(e); } });
      el.addEventListener("pointermove", (e) => { if (e.pointerType === "mouse") move(e); });
      el.addEventListener("pointerleave", () => {
        cancelAnimationFrame(raf);
        el.classList.remove("is-tilt");
        ["--rx", "--ry", "--px", "--py"].forEach((v) => el.style.removeProperty(v));
      });
    });
  }

  /* ───────── 地圖：浮起、金線描邊、其他縣淡出、浮動標籤 ───────── */
  const enhanceMap = (box, opts = {}) => {
    const svg = $(".atlas-map", box);
    if (!svg) return null;
    const lift = $(".lift", svg), tip = $(".map-tip", box);
    let active = null, pointer = "mouse";
    const toBox = (x, y) => {
      const m = svg.getScreenCTM(), r = box.getBoundingClientRect();
      const p = new DOMPoint(x, y).matrixTransform(m);
      return [p.x - r.left, p.y - r.top];
    };
    const off = () => {
      if (!active) return;
      active.classList.remove("is-active");
      svg.classList.remove("has-active");
      lift.replaceChildren();
      $$(".pf-dot.is-active", svg).forEach((d) => d.classList.remove("is-active"));
      tip && tip.classList.remove("is-on");
      active = null;
    };
    const on = (a) => {
      if (active === a) return;
      off();
      active = a;
      a.classList.add("is-active");
      svg.classList.add("has-active");
      const path = $("path", a);
      const fill = path.cloneNode(), line = path.cloneNode();
      fill.setAttribute("class", "lift-fill");
      line.setAttribute("class", "lift-line");
      line.setAttribute("pathLength", "1");
      lift.replaceChildren(fill, line);
      $(`.pf-dot[data-pref="${a.dataset.pref}"]`, svg)?.classList.add("is-active");
      if (tip) {
        $("b", tip).textContent = a.dataset.name;
        $("span", tip).textContent = `${a.dataset.n} 款`;
        const [x, y] = toBox(Number(a.dataset.cx), Number(a.dataset.cy));
        tip.style.left = `${x}px`;
        tip.style.top = `${y}px`;
        tip.classList.add("is-on");
      }
      opts.onFocus && opts.onFocus(a.dataset.pref, pointer);
    };
    box.addEventListener("pointerdown", (e) => (pointer = e.pointerType), { capture: true });
    $$(".pf.is-rec", svg).forEach((a) => {
      a.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") on(a); });
      a.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") off(); });
      a.addEventListener("pointerdown", (e) => { if (e.pointerType !== "mouse") a._armed = active === a; });
      a.addEventListener("focus", () => on(a));
      a.addEventListener("blur", off);
      a.addEventListener("click", (e) => {
        /* 觸控：第一次點是預覽，第二次點才進入縣別頁 */
        if (pointer !== "mouse" && !a._armed) { e.preventDefault(); on(a); a._armed = true; }
      });
    });
    return { on, off, svg };
  };
  const asset = (p) => (window.SA_ASSET ? window.SA_ASSET(p) : p);

  /* ───────── 首頁地圖與右頁 ───────── */
  const atlas = $("[data-atlas]");
  const leaf = $("#leaf");
  const dataNode = $("#atlas-data");
  if (atlas && leaf && dataNode) {
    const data = JSON.parse(dataNode.textContent);
    let current = "";

    const tpl = (s, isAll) => {
      const seals = s.seals.map((t, n) => seal(t, `leaf-seal s${n}`, ((n * 37) % 9) - 4)).join("");
      const picks = s.picks.map((p) => `<li><a href="./sake/${p.id}/">${esc(p.t)}</a></li>`).join("");
      const href = isAll ? "./sake/" : `./pref/${s.slug}/`;
      const cta = isAll ? `瀏覽全部 ${s.n} 款` : `看${esc(s.name)}的 ${s.n} 款`;
      const tail = isAll
        ? '<p class="leaf-hint">把滑鼠移到地圖上的縣，這一頁會換成那裡的紀錄。</p>'
        : '<button type="button" class="linkish" data-reset>回到全日本</button>';
      const scene = s.sc ? `<img class="leaf-scene" src="${asset(`./assets/scenes/${s.sc}.webp`)}" alt="" aria-hidden="true" decoding="async">` : "";
      const cap = s.cap ? `<p class="leaf-scene-cap">${esc(s.cap)}</p>` : "";
      return `<div class="leaf-top">
        ${scene}
        <div class="leaf-ink">
          <p class="leaf-area">${esc(s.area)}</p>
          <h2 class="leaf-title">${esc(s.name)}</h2>
          <p class="leaf-count"><span class="tcy">${s.n}</span>款<span class="gap"></span><span class="tcy">${s.b}</span>間酒造</p>
        </div>
        <div class="leaf-seals">${seals}</div>
        <div class="leaf-side">${cap}<p class="leaf-date">${s.date ? "最近一次　" + esc(s.date) : ""}</p></div>
      </div>
      <div class="leaf-foot">
        <ul class="leaf-picks" aria-label="${esc(s.name)}的酒款">${picks}</ul>
        <a class="btn" href="${href}">${cta}${icon.arrow}</a>
        ${tail}
      </div>`;
    };

    const show = (key) => {
      if (key === current) return;
      current = key;
      (leaf.querySelector(".leaf-body") || leaf).innerHTML = tpl(data[key || "_all"], !key);
      leaf.classList.remove("is-stamping");
      if (!reduce.matches) {
        void leaf.offsetWidth;
        leaf.classList.add("is-stamping");
      }
    };

    /* 預先載入各縣的畫，換頁時不會閃 */
    const warm = () => Object.values(data).forEach((d) => { if (d.sc) { const i = new Image(); i.src = asset(`./assets/scenes/${d.sc}.webp`); } });
    if ("requestIdleCallback" in window) requestIdleCallback(warm, { timeout: 2500 });
    else setTimeout(warm, 1200);

    const map = enhanceMap(atlas, {
      onFocus: (key, pointer) => {
        show(key);
        if (pointer !== "mouse") {
          const r = leaf.getBoundingClientRect();
          if (r.top > innerHeight - 120) leaf.scrollIntoView({ behavior: reduce.matches ? "auto" : "smooth", block: "start" });
        }
      },
    });
    leaf.addEventListener("click", (e) => {
      if (e.target.closest("[data-reset]")) {
        show("");
        map && map.off();
        $(".leaf .btn")?.focus({ preventScroll: true });
      }
    });

    /* 區域圖例：滑過時只亮起該區的縣 */
    const svg = map && map.svg;
    $$(".areas a").forEach((a) => {
      const hl = () => {
        svg.classList.add("has-hl");
        $$(".pf.is-rec", svg).forEach((p) => p.classList.toggle("is-hl", p.dataset.area === a.dataset.area));
      };
      const unhl = () => {
        svg.classList.remove("has-hl");
        $$(".pf.is-hl", svg).forEach((p) => p.classList.remove("is-hl"));
      };
      a.addEventListener("pointerenter", hl);
      a.addEventListener("focus", hl);
      a.addEventListener("pointerleave", unhl);
      a.addEventListener("blur", unhl);
    });
  }

  /* 縣別頁的小地圖：同樣的浮起與標籤 */
  const lite = $("[data-atlas-lite]");
  if (lite) enhanceMap(lite);

  /* ───────── 全部酒款：篩選 ───────── */
  const form = $("#filters");
  const grid = $("#cards");
  if (form && grid) {
    const cards = $$(".card", grid);
    const total = cards.length;
    const count = $("#ex-count");
    const empty = $("#empty");
    const reset = $(".f-reset", form);
    const wrap = $(".ex");
    const params = new URLSearchParams(NAV.search());
    const names = ["q", "area", "pref", "type", "rice", "fl", "pol", "sort"];
    const prefOptions = $$('select[name="pref"] option', form);
    const collator = new Intl.Collator("zh-Hant");

    for (const n of names) {
      const v = params.get(n);
      const el = form.elements[n];
      if (!v || !el) continue;
      if (el.tagName === "SELECT" && ![...el.options].some((o) => o.value === v)) {
        el.append(new Option(n === "pol" ? `${v}% 以下` : v, v));
      }
      el.value = v;
    }
    for (const n of ["photo", "note"]) if (params.get(n)) form.elements[n].checked = true;

    const syncPref = () => {
      const area = form.elements.area.value;
      prefOptions.forEach((o) => (o.hidden = !!(o.value && area && o.dataset.area !== area)));
      const sel = form.elements.pref.selectedOptions[0];
      if (sel && sel.hidden) form.elements.pref.value = "";
    };

    const setView = (v) => {
      grid.dataset.view = v;
      wrap.classList.toggle("is-list", v === "list");
      $$(".f-view button", form).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.view === v)));
    };

    let lastOrder = "";
    const apply = () => {
      const f = Object.fromEntries(new FormData(form));
      const terms = (f.q || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
      let n = 0;
      for (const c of cards) {
        const d = c.dataset;
        const ok =
          (!f.area || d.area === f.area) &&
          (!f.pref || d.pref === f.pref) &&
          (!f.type || d.type === f.type) &&
          (!f.rice || d.rice.split("|").some((r) => r.includes(f.rice))) &&
          (!f.fl || (d.fl || "").split("|").includes(f.fl)) &&
          (!f.pol || (d.pol !== "" && Number(d.pol) <= Number(f.pol))) &&
          (!f.photo || d.photo === "1") &&
          (!f.note || d.note === "1") &&
          terms.every((t) => d.q.includes(t));
        c.hidden = !ok;
        if (ok) n++;
      }
      const sort = f.sort || "";
      if (sort !== lastOrder) {
        const sorted = [...cards].sort((a, b) => {
          if (sort === "latest") return b.dataset.latest - a.dataset.latest || a.dataset.order - b.dataset.order;
          if (sort === "like") return (Number(b.dataset.like) || 0) - (Number(a.dataset.like) || 0) || a.dataset.order - b.dataset.order;
          if (sort === "name") return collator.compare(a.querySelector(".c-brand").textContent, b.querySelector(".c-brand").textContent);
          return a.dataset.order - b.dataset.order;
        });
        grid.append(...sorted);
        lastOrder = sort;
      }
      count.textContent = n === total ? `${total} 款` : `符合 ${n} 款，共 ${total} 款`;
      empty.hidden = n > 0;
      const active = Object.entries(f).some(([k, v]) => k !== "sort" && v);
      reset.hidden = !active;

      const out = new URLSearchParams();
      for (const [k, v] of Object.entries(f)) if (v) out.set(k, v);
      if (grid.dataset.view === "list") out.set("view", "list");
      NAV.replace(out.toString());
    };

    const withTransition = (fn) => {
      if (document.startViewTransition && !reduce.matches) document.startViewTransition(fn);
      else fn();
    };

    let t;
    form.addEventListener("input", (e) => {
      if (e.target.type !== "search") return;
      clearTimeout(t);
      t = setTimeout(apply, 120);
    });
    form.addEventListener("change", (e) => {
      if (e.target.type === "search") return;
      if (e.target.name === "area") syncPref();
      withTransition(apply);
    });
    form.addEventListener("submit", (e) => e.preventDefault());
    form.addEventListener("reset", () => setTimeout(() => { syncPref(); withTransition(apply); }));
    $("[data-clear]")?.addEventListener("click", () => form.reset());
    $$(".f-view button", form).forEach((b) =>
      b.addEventListener("click", () => withTransition(() => { setView(b.dataset.view); apply(); }))
    );

    setView(params.get("view") === "list" ? "list" : "grid");
    syncPref();
    apply();
    if (params.get("focus")) $("#f-q")?.focus();
  }

  /* ───────── 入門：分類表 ───────── */
  const mxData = $("#mx-data");
  if (mxData) {
    const d = JSON.parse(mxData.textContent);
    const panel = $("#mx-panel");
    const buttons = $$(".matrix button[data-type]");
    const pick = (b) => {
      const t = b.dataset.type;
      buttons.forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      const list = d.items[t] || [];
      const lis = list.slice(0, 24).map((x) => `<li><a href="../sake/${x.id}/">${esc(x.t)}</a></li>`).join("");
      panel.innerHTML = `<h3>${esc(t)}</h3><p>${esc(d.defs[t] || "")}</p>` +
        (list.length
          ? `<ul>${lis}</ul><a class="btn" href="../sake/?type=${encodeURIComponent(t)}">看全部 ${list.length} 款${icon.arrow}</a>`
          : "<p>圖鑑裡還沒有記錄這一種。</p>");
      panel.classList.remove("is-swap");
      if (!reduce.matches) { void panel.offsetWidth; panel.classList.add("is-swap"); }
    };
    buttons.forEach((b) => b.addEventListener("click", () => pick(b)));
    const fromHash = NAV.fragment();
    const initial = buttons.find((b) => b.dataset.type === fromHash) || buttons.find((b) => b.dataset.type === "純米吟釀");
    if (initial) pick(initial);
  }

  /* ───────── 入門：精米步合 ───────── */
  const pol = $("[data-polisher]");
  if (pol) {
    const input = $("#pol", pol), out = $("#pol-out", pol), say = $("#pol-say", pol), dia = $("#pol-dia", pol), colEl = $("#pol-col", pol);
    const g = $(".grain-left", pol);
    const list = JSON.parse(($("#pol-data", pol) || { textContent: "[]" }).textContent);
    const sayFor = (v) => {
      const gone = 100 - v;
      if (v >= 100) return "還沒有磨，這是一粒糙米的大小。";
      if (v > 70) return `磨掉了 ${gone}%。我們平常吃的白米，大約留下九成左右。`;
      if (v > 60) return `磨掉了 ${gone}%。70% 以下是本釀造的門檻；純米酒則沒有精米步合的限制。`;
      if (v > 50) return `磨掉了 ${gone}%。60% 以下，可以標示為吟釀或純米吟釀。`;
      if (v > 20) return `磨掉了 ${gone}%。50% 以下，可以標示為大吟釀或純米大吟釀。`;
      if (v > 9) return `磨掉了 ${gone}%。磨到兩成以下已經是極少數的高精白酒，一粒米只剩中心一小顆，精米要花上好幾天。`;
      return `磨掉了 ${gone}%。精米步合只有個位數的酒非常稀有，是酒造挑戰極限的作品。`;
    };
    const update = () => {
      const v = Number(input.value);
      const [rx, ry] = grainGeom(v / 100, 58, 82);
      g.setAttribute("rx", rx.toFixed(2)); g.setAttribute("ry", ry.toFixed(2));
      out.textContent = v;
      say.textContent = sayFor(v);
      dia.textContent = `重量剩 ${v}%，米粒的直徑大約是原本的 ${Math.round(Math.cbrt(v / 100) * 100)}%。`;
      const hits = list.filter((x) => x[0] <= v);
      colEl.innerHTML = hits.length
        ? `圖鑑裡磨到 ${v}% 以下的有 ${hits.length} 款` + (v < 100 ? `，最低是 <a href="../sake/${hits[0][1]}/">${esc(hits[0][2])}</a>（${hits[0][0]}%）。` : "。")
        : `圖鑑裡還沒有磨到 ${v}% 以下的酒。`;
    };
    input.addEventListener("input", update);
    update();
  }

  /* ───────── 首頁：依香氣找 ───────── */
  const scent = $(".scent");
  if (scent) {
    const chips = $$("[data-scent]", scent), lis = $$(".fold-track > li", scent), track = $(".fold-track", scent);
    const pick = (tag) => {
      const run = () => {
        chips.forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.scent === tag)));
        lis.forEach((li) => { li.hidden = !li.dataset.aroma.split("|").includes(tag); });
        track.scrollLeft = 0;
      };
      if (document.startViewTransition && !reduce.matches) document.startViewTransition(run);
      else run();
    };
    chips.forEach((c) => c.addEventListener("click", () => pick(c.dataset.scent)));
  }

  /* ───────── 酒款頁：風味（香氣輪、口感墨形、心得裡的風味詞） ───────── */
  $$(".fl-tip").forEach((n) => n.remove());
  const flSec = $("[data-flavor]");
  if (flSec) {
    const D = JSON.parse($(".fl-data", flSec).textContent);
    const info = D.info;
    const sayT = $("[data-say-t]", flSec), sayD = $("[data-say-d]", flSec), sayMore = $("[data-say-more]", flSec);
    const coreBox = $(".wheel-core", flSec), coreWord = $("[data-core-word]", flSec), coreFam = $("[data-core-fam]", flSec);
    const mine = new Set([...D.aroma, ...D.palate]);

    /* 口感：利き猪口，滑過口感詞時杯中的酒會盪一下 */
    const cupBox = $("[data-cup]", flSec);
    const react = (tag) => {
      if (!cupBox || reduce.matches) return;
      cupBox.dataset.react = (info[tag] && info[tag].shape) || "any";
      cupBox.classList.remove("is-burst"); void cupBox.offsetWidth; cupBox.classList.add("is-burst");
    };
    if (cupBox) cupBox.addEventListener("click", () => react(D.palate[0] || ""));
    let ink = null;
    const inkBox = $("[data-ink]", flSec);
    if (inkBox) {
      const body = $(".ink-body", inkBox), bleed = $(".ink-bleed", inkBox), core = $(".ink-core", inkBox), bub = $(".ink-bubbles", inkBox);
      const svg = $("svg", inkBox);
      const N = 96;
      const traitsOf = (list) => { const t = {}; list.forEach((x) => { const sh = info[x] && info[x].shape; if (sh) t[sh] = 1; }); return t; };
      const radii = (t) => {
        const R = 84 * (1 + 0.2 * (t.full || 0) - 0.16 * (t.light || 0));
        const out = [];
        for (let i = 0; i < N; i++) {
          const th = (i / N) * Math.PI * 2;
          let irr = 0.05 * Math.sin(3 * th + 0.7) + 0.034 * Math.sin(5 * th + 2.1) + 0.02 * Math.sin(7 * th + 0.3);
          irr *= 1 - 0.65 * (t.smooth || 0) - 0.5 * (t.round || 0);
          const n = 5, seg = (2 * Math.PI) / n;
          const poly = Math.cos(Math.PI / n) / Math.cos((((th + Math.PI / 2) % seg) + seg) % seg - Math.PI / n);
          const sharp = (t.sharp || 0) * 0.62;
          let r = (1 - sharp) + poly * 0.94 * sharp;
          r += irr + 0.05 * (t.acid || 0) * Math.sin(13 * th);
          r += 0.1 * (t.sweet || 0) * Math.pow(Math.max(0, Math.sin(th)), 3);
          out.push(R * r);
        }
        return out;
      };
      const pathOf = (rs) => {
        const P = rs.map((r, i) => { const th = (i / N) * Math.PI * 2; return [r * Math.cos(th), r * Math.sin(th)]; });
        let d = `M${P[0][0].toFixed(1)} ${P[0][1].toFixed(1)}`;
        for (let i = 0; i < N; i++) {
          const p0 = P[(i - 1 + N) % N], p1 = P[i], p2 = P[(i + 1) % N], p3 = P[(i + 2) % N];
          d += `C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)} ${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)} ${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
        }
        return d + "Z";
      };
      const style = (t) => {
        const a0 = t.light ? 0.2 : t.full ? 0.72 : 0.42, a1 = t.light ? 0.3 : t.full ? 0.84 : 0.58, a2 = t.light ? 0.52 : t.full ? 0.98 : 0.86;
        svg.style.setProperty("--a0", a0); svg.style.setProperty("--a1", a1); svg.style.setProperty("--a2", a2);
        inkBox.classList.toggle("is-sweet", !!t.sweet);
        core.setAttribute("r", t.bitter ? 26 : 0);
        bleed.style.opacity = t.umami ? 0.26 : 0.1;
        bub.innerHTML = t.fizz
          ? Array.from({ length: 13 }, (_, i) => {
              const a = (i * 137.5 * Math.PI) / 180, rr = 8 + ((i * 29) % 46);
              return `<circle cx="${(Math.cos(a) * rr).toFixed(1)}" cy="${(Math.sin(a) * rr * 0.8 + 18).toFixed(1)}" r="${(2.2 + (i % 3) * 0.9).toFixed(1)}" style="animation-delay:${(i * 0.21).toFixed(2)}s"/>`;
            }).join("")
          : "";
      };
      let cur = null, raf = 0;
      const morph = (list) => {
        const t = traitsOf(list), target = radii(t);
        style(t);
        cancelAnimationFrame(raf);
        if (!cur || reduce.matches) { cur = target; const d = pathOf(cur); body.setAttribute("d", d); bleed.setAttribute("d", d); return; }
        const from = cur.slice(), t0 = performance.now(), dur = 460;
        const step = (now) => {
          const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
          cur = from.map((r, i) => r + (target[i] - r) * e);
          const d = pathOf(cur); body.setAttribute("d", d); bleed.setAttribute("d", d);
          if (k < 1) raf = requestAnimationFrame(step);
        };
        raf = requestAnimationFrame(step);
      };
      ink = { morph };
      morph(D.palate);
    }

    const sameHtml = (tag) => {
      const list = D.same[tag] || [];
      if (!list.length) return "";
      const links = list.map((x) => `<a href="${D.base}sake/${x.id}/">${esc(x.t)}</a>`).join("、");
      return `同樣有「${esc(tag)}」的酒：${links}　<a href="${D.base}sake/?fl=${encodeURIComponent(tag)}">看全部</a>`;
    };
    const summary = () => {
      sayT.textContent = "這支酒的風味";
      const parts = [];
      if (D.aroma.length) parts.push(`香氣：${D.aroma.join("、")}`);
      if (D.palate.length) parts.push(`口感：${D.palate.join("、")}`);
      sayD.textContent = parts.join("。") + "。";
      sayMore.textContent = "";
    };
    let focused = "";
    const mark = (tag) => {
      $$("[data-fl]").forEach((el) => { if (!el.classList.contains("card")) el.classList.toggle("is-focus", !!tag && el.dataset.fl === tag); });
      $$(".wh-fam", flSec).forEach((el) => el.classList.toggle("is-focus", !!tag && info[tag] && el.dataset.fam === info[tag].fam));
    };
    const focus = (tag) => {
      const it = info[tag];
      if (!it || tag === focused) return;
      focused = tag;
      mark(tag);
      sayT.textContent = it.kind === "aroma" && it.fam !== "其他" ? `${tag}・${it.fam}` : tag;
      sayD.textContent = (mine.has(tag) ? "" : "（這支酒沒有記錄到）") + it.desc;
      sayMore.innerHTML = sameHtml(tag);
      flSec.classList.add("is-saying");
      if (it.kind === "aroma" && coreWord && it.fam !== "其他") {
        coreWord.textContent = tag; coreFam.textContent = it.fam;
        coreBox.classList.remove("is-swap"); void coreBox.offsetWidth; if (!reduce.matches) coreBox.classList.add("is-swap");
      }
      if (it.kind === "palate") { if (ink) ink.morph([tag]); react(tag); }
    };
    const release = () => { if (ink && focused && info[focused] && info[focused].kind === "palate") ink.morph(D.palate); };

    let tipEl = null;
    const tip = (el, tag) => {
      if (!el || !el.classList.contains("fw")) { tipEl && tipEl.classList.remove("is-on"); return; }
      if (!tipEl) { tipEl = document.createElement("div"); tipEl.className = "fl-tip"; tipEl.setAttribute("role", "tooltip"); document.body.append(tipEl); }
      const it = info[tag];
      tipEl.innerHTML = `<b>${esc(it.kind === "aroma" && it.fam !== "其他" ? tag + "・" + it.fam : tag)}</b>${esc(it.desc)}`;
      const r = el.getBoundingClientRect(), w = Math.min(280, innerWidth - 24);
      tipEl.style.width = w + "px";
      tipEl.style.left = Math.max(12, Math.min(innerWidth - w - 12, r.left + r.width / 2 - w / 2)) + scrollX + "px";
      tipEl.style.top = r.bottom + scrollY + 10 + "px";
      tipEl.classList.add("is-on");
    };
    $$("[data-fl]").filter((el) => !el.classList.contains("card") && (el.closest("[data-flavor]") === flSec || el.classList.contains("fw"))).forEach((el) => {
      const tag = el.dataset.fl;
      el.addEventListener("pointerenter", (e) => { if (e.pointerType === "mouse") { focus(tag); tip(el, tag); } });
      el.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") { release(); tip(null); } });
      el.addEventListener("focus", () => { focus(tag); tip(el, tag); });
      el.addEventListener("blur", () => { release(); tip(null); });
      el.addEventListener("click", () => { focused = ""; focus(tag); tip(el, tag); });
    });
    summary();
  }

  /* ───────── 酒款頁：斟一杯 ───────── */
  const pour = $("[data-pour]");
  if (pour) {
    const go = () => { pour.classList.remove("is-poured"); void pour.offsetWidth; pour.classList.add("is-poured"); };
    if (reduce.matches || !("IntersectionObserver" in window)) pour.classList.add("is-poured");
    else {
      const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { io.disconnect(); go(); } }, { rootMargin: "0px 0px -20% 0px" });
      io.observe(pour);
    }
    $(".pour-glass", pour).addEventListener("click", go);
    /* 同一支酒喝過不只一次：切換是哪一次，杯子就倒那一次的量 */
    const tabs = $$(".pour-tabs [role=tab]", pour);
    tabs.forEach((b) => b.addEventListener("click", () => {
      tabs.forEach((x) => x.setAttribute("aria-selected", String(x === b)));
      pour.style.setProperty("--off", `${b.dataset.off}px`);
      const v = $(".pour-vol", pour), w = $(".pour-where", pour);
      if (v) v.textContent = b.dataset.meta;
      if (w) w.textContent = b.dataset.where;
      go();
    }));
  }

  /* ───────── 酒款頁：米粒（從整粒米磨到這支酒的精米步合） ───────── */
  const grain = $("[data-grain]");
  if (grain) {
    const target = Number(grain.dataset.p), g = $(".grain-left", grain), num = $("[data-grain-num]", grain);
    const finalTxt = num.textContent, decimals = finalTxt.includes(".") ? 1 : 0;
    const draw = (p) => {
      const [rx, ry] = grainGeom(p, 44, 62);
      g.setAttribute("rx", rx.toFixed(2)); g.setAttribute("ry", ry.toFixed(2));
    };
    const run = () => {
      const dur = 900 + 1100 * (1 - target), t0 = performance.now();
      const step = (now) => {
        const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3), p = 1 + (target - 1) * e;
        draw(p);
        num.textContent = k < 1 ? (p * 100).toFixed(decimals) : finalTxt;
        if (k < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    if (!reduce.matches && "IntersectionObserver" in window) {
      draw(1); num.textContent = "100";
      const io = new IntersectionObserver((es) => {
        if (es.some((e) => e.isIntersecting)) { io.disconnect(); run(); }
      }, { rootMargin: "0px 0px -15% 0px" });
      io.observe(grain);
    }
  }
  }

  window.SA_INIT = init;
  if (!window.SA_NAV) init();
})();
