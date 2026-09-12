/* feed-ranker console: the reader's own ranking profile, editable. */
/* feed-ranker: ranking console. A character sheet for the reader's
   own ranking profile: every signal as a row with its exact value,
   editable in place, with pause/resume for learning. The page mounts
   one console and drives it:

     FeedRanker.console.mount({
       buttonHost:  element,  // the CONSOLE button is appended here
       panelHost:   element,  // the panel is appended here
       getMode:     function () -> 'foryou' when For You is active,
       getItems:    function () -> [{ id, item, el }] visible items,
       getAllItems: function () -> [{ id, item, el }] all rankable items
                   (optional; falls back to getItems; used to seed the
                   console rows with the full topic/source/kind
                   vocabulary so the panel is useful before anything
                   has been learned),
       stickySel:   CSS selector of a sticky bar that can overlap the
                   panel when stuck (optional; the console nudges the
                   page just enough to clear it on open),
       rerank:      function () -> re-apply the For You ordering,
       placeWhy:    function (entry, btn) -> put the why button in the
                                  item's DOM (page-specific positioning)
     });

   The page must call api.sync() whenever the sort mode or the visible
   item set changes. The console shows the CONSOLE button and the per
   item "why ranked" markers only while For You is active. All edits
   are the reader's explicit action; the console never writes to the
   profile on its own. */
(function (root) {
  'use strict';

  var FeedRanker = root.FeedRanker;
  if (!FeedRanker || !FeedRanker.profile || !FeedRanker.ranker) return;
  if (typeof document === 'undefined') return;

  var CSS = [
    '.frk-console-btn{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;',
    'font-size:11px;letter-spacing:.12em;text-transform:uppercase;background:transparent;',
    'color:inherit;border:1px solid rgba(128,128,128,.5);padding:6px 10px;cursor:pointer;border-radius:0}',
    '.frk-console-btn:hover{border-color:currentColor}',
    '.frk-panel{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;',
    'line-height:1.5;color:inherit;border-top:1px solid rgba(128,128,128,.35);',
    'border-bottom:1px solid rgba(128,128,128,.35);margin:12px 0;padding:12px 0}',
    '.frk-head{display:flex;flex-wrap:wrap;gap:6px 16px;align-items:baseline;justify-content:space-between}',
    '.frk-title{font-size:11px;letter-spacing:.16em;opacity:.75}',
    '.frk-status{font-weight:700;letter-spacing:.08em}',
    '.frk-counts{opacity:.6;font-size:11px}',
    '.frk-actions{display:flex;gap:8px;flex-wrap:wrap}',
    '.frk-btn{font:inherit;font-size:11px;letter-spacing:.1em;text-transform:uppercase;background:transparent;',
    'color:inherit;border:1px solid rgba(128,128,128,.5);padding:5px 10px;cursor:pointer;border-radius:0}',
    '.frk-btn:hover{border-color:currentColor}',
    '.frk-firstopen{opacity:.7;margin:10px 0 0;max-width:60ch}',
    '.frk-group{margin-top:14px}',
    '.frk-group-title{font-size:11px;letter-spacing:.16em;opacity:.6;',
    'border-bottom:1px solid rgba(128,128,128,.35);padding-bottom:4px;margin-bottom:2px}',
    '.frk-row{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:center;',
    'padding:6px 0;border-bottom:1px dotted rgba(128,128,128,.22)}',
    '.frk-name{flex:1 1 120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.frk-val{flex:0 0 52px;text-align:right;font-variant-numeric:tabular-nums}',
    '.frk-bar{flex:1 1 100%;position:relative;height:7px;background:rgba(128,128,128,.18)}',
    '.frk-bar i{position:absolute;top:0;bottom:0;background:currentColor;opacity:.7;display:block}',
    '.frk-basis{flex:0 0 auto;font-size:11px;opacity:.55}',
    '.frk-release{background:none;border:0;padding:0;font:inherit;color:inherit;text-decoration:underline;cursor:pointer}',
    '.frk-row input[type=range]{flex:1 1 140px;accent-color:currentColor;margin:0}',
    '.frk-empty{opacity:.5;font-size:11px;padding:6px 0}',
    '.frk-blend{opacity:.5;font-size:11px;margin-top:14px}',
    '.frk-why{position:absolute;background:transparent;border:0;color:inherit;opacity:0;',
    'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11px;',
    'letter-spacing:.08em;cursor:pointer;padding:4px 8px;white-space:nowrap}',
    '.feed-row-wrap:hover .frk-why,.frk-why:focus-visible{opacity:.75}',
    'article.research-note:hover .frk-why{opacity:.75}',
    '.frk-why:hover{opacity:1 !important;text-decoration:underline}',
    '.frk-why-detail{border-top:1px dotted rgba(128,128,128,.35);margin-top:6px;padding:8px 0;',
    'font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}',
    '.frk-why-line{display:block;width:100%;text-align:left;background:transparent;border:0;color:inherit;',
    'font:inherit;padding:4px 0;cursor:pointer}',
    '.frk-why-line:hover{text-decoration:underline}',
    '.frk-why-none{opacity:.6;font-size:11px}',
    '.frk-flash{outline:1px solid currentColor;outline-offset:2px}'
  ].join('\n');

  function ensureCSS() {
    if (document.getElementById('frk-console-css')) return;
    var s = document.createElement('style');
    s.id = 'frk-console-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function fmtVal(v) {
    v = Math.round(v * 100) / 100;
    return (v < 0 ? '-' : '+') + Math.abs(v).toFixed(2);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = text;
    return e;
  }

  function mount(cfg) {
    ensureCSS();

    var btn = el('button', 'frk-console-btn', 'CONSOLE');
    btn.type = 'button';
    btn.setAttribute('aria-expanded', 'false');
    btn.hidden = true;
    cfg.buttonHost.appendChild(btn);

    var panel = el('section', 'frk-panel');
    panel.hidden = true;
    panel.setAttribute('aria-label', 'Ranking console');
    cfg.panelHost.appendChild(panel);

    var open = false;
    var whyNodes = []; // { btn, detail }

    function snapshot() { return FeedRanker.profile.getSnapshot(); }

    function setOpen(v) {
      open = v;
      panel.hidden = !v;
      btn.setAttribute('aria-expanded', String(v));
      if (v) { render(); reveal(); }
    }

    // If a sticky bar (the feed's stuck controls, for example) paints
    // over the freshly opened panel, nudge the page just enough to
    // clear it. No-op when there is no overlap.
    function reveal() {
      if (!cfg.stickySel || typeof document === 'undefined') return;
      var bar;
      try { bar = document.querySelector(cfg.stickySel); } catch (e) { return; }
      if (!bar) return;
      var rb = bar.getBoundingClientRect();
      var rp = panel.getBoundingClientRect();
      if (rb.bottom > rp.top + 1) {
        window.scrollBy({ top: (rb.bottom - rp.top) + 12, behavior: 'smooth' });
      }
    }

    btn.addEventListener('click', function () { setOpen(!open); });

    function barFill(bar, v) {
      bar.innerHTML = '';
      var i = document.createElement('i');
      if (v >= 0) {
        i.style.left = '50%';
        i.style.width = (v * 50) + '%';
      } else {
        i.style.left = (50 + v * 50) + '%';
        i.style.width = (-v * 50) + '%';
      }
      bar.appendChild(i);
    }

    // A "set by you" row is pinned: learning skips it until the user
    // releases it back to measured (value stays, learning resumes
    // from there) or resets the profile.
    function showPinned(basis, r, group) {
      basis.textContent = '';
      basis.appendChild(document.createTextNode('set by you '));
      var rel = el('button', 'frk-release', 'release');
      rel.setAttribute('aria-label',
        'release ' + r.key + ' back to measured');
      rel.title = 'Let learning adjust this signal again';
      rel.addEventListener('click', function () {
        FeedRanker.profile.releaseAffinity(group, r.key);
        r.basis = 'measured';
        basis.textContent = 'measured';
      });
      basis.appendChild(rel);
    }

    function groupBlock(title, rowsArr, group) {
      var g = el('div', 'frk-group');
      g.appendChild(el('div', 'frk-group-title', title));
      if (!rowsArr.length) {
        g.appendChild(el('div', 'frk-empty', 'No signals yet.'));
        return g;
      }
      rowsArr.forEach(function (r) {
        var row = el('div', 'frk-row');
        row.setAttribute('data-frk-group', group);
        row.setAttribute('data-frk-key', r.key);
        var name = el('span', 'frk-name', r.key);
        name.title = r.key;
        var val = el('span', 'frk-val', fmtVal(r.value));
        var bar = el('div', 'frk-bar');
        bar.setAttribute('aria-hidden', 'true');
        barFill(bar, r.value);
        var basis = el('span', 'frk-basis');
        if (r.basis === 'set by you') showPinned(basis, r, group);
        else basis.textContent = 'measured';
        var slider = document.createElement('input');
        slider.type = 'range';
        slider.min = '-1';
        slider.max = '1';
        slider.step = '0.05';
        slider.value = String(Math.round(r.value * 20) / 20);
        slider.setAttribute('aria-label', title.toLowerCase() + ' signal ' + r.key);
        slider.addEventListener('input', function () {
          var v = parseFloat(slider.value, 10);
          FeedRanker.profile.setAffinity(group, r.key, v);
          r.value = v;
          r.basis = 'set by you';
          val.textContent = fmtVal(v);
          showPinned(basis, r, group);
          barFill(bar, v);
          try { cfg.rerank(); } catch (e) {}
        });
        row.appendChild(name);
        row.appendChild(val);
        row.appendChild(bar);
        row.appendChild(basis);
        row.appendChild(slider);
        g.appendChild(row);
      });
      return g;
    }

    // Rows come from the profile snapshot, seeded with the full
    // vocabulary of the rankable items: a fresh reader sees every
    // topic/source/kind at +0.00 (measured, nothing learned yet) with
    // a working slider, instead of an empty panel. Learned and pinned
    // rows keep their values and sort first.
    function seeded(snapRows, group) {
      var seen = {};
      snapRows.forEach(function (r) { seen[r.key] = true; });
      var items = [];
      try { items = ((cfg.getAllItems || cfg.getItems)() || []); } catch (e) {}
      items.forEach(function (entry) {
        var it = (entry && entry.item) || entry || {};
        var keys = group === 'topic' ? (it.topics || [])
          : group === 'source' ? (it.source ? [it.source] : [])
          : (it.kind ? [it.kind] : []);
        keys.forEach(function (k) {
          if (k && !seen[k]) {
            seen[k] = true;
            snapRows.push({ key: k, value: 0, basis: 'measured' });
          }
        });
      });
      snapRows.sort(function (a, b) {
        if (b.value !== a.value) return b.value - a.value;
        return a.key < b.key ? -1 : a.key > b.key ? 1 : 0;
      });
      return snapRows;
    }

    function render() {
      var snap = snapshot();
      panel.innerHTML = '';

      var head = el('div', 'frk-head');
      head.appendChild(el('span', 'frk-title', 'RANKING CONSOLE'));
      head.appendChild(el('span', 'frk-status',
        snap.paused ? 'LEARNING: PAUSED' : 'LEARNING: ON'));
      head.appendChild(el('span', 'frk-counts',
        snap.counts.reads + ' READS \u00b7 ' +
        snap.counts.skips + ' SKIPS \u00b7 ' +
        snap.counts.dismissed + ' HIDDEN'));
      var actions = el('span', 'frk-actions');
      var pauseBtn = el('button', 'frk-btn',
        snap.paused ? 'Resume learning' : 'Pause learning');
      pauseBtn.type = 'button';
      pauseBtn.addEventListener('click', function () {
        FeedRanker.profile.setPaused(!snap.paused);
        render();
        syncButton();
      });
      var resetBtn = el('button', 'frk-btn', 'Reset');
      resetBtn.type = 'button';
      // Two-step inline confirm: no native dialog, the button itself
      // becomes the question and disarms after a few seconds.
      var resetArmed = false, resetTimer = null;
      resetBtn.addEventListener('click', function () {
        if (!resetArmed) {
          resetArmed = true;
          resetBtn.textContent = 'Confirm reset?';
          resetTimer = setTimeout(function () {
            resetArmed = false;
            if (resetBtn.isConnected) resetBtn.textContent = 'Reset';
          }, 4000);
          return;
        }
        clearTimeout(resetTimer);
        resetArmed = false;
        FeedRanker.profile.resetProfile();
        render();
        try { cfg.rerank(); } catch (e) {}
      });
      actions.appendChild(pauseBtn);
      actions.appendChild(resetBtn);
      head.appendChild(actions);
      panel.appendChild(head);

      panel.appendChild(el('p', 'frk-firstopen',
        'This panel shows the signals that order For you. ' +
        'Adjusting them only changes ordering.'));

      panel.appendChild(groupBlock('TOPICS', seeded(snap.topics, 'topic'), 'topic'));
      panel.appendChild(groupBlock('SOURCES', seeded(snap.sources, 'source'), 'source'));
      panel.appendChild(groupBlock('KINDS', seeded(snap.kinds, 'kind'), 'kind'));

      var w = snap.weights;
      panel.appendChild(el('div', 'frk-blend',
        'BLEND recency ' + w.recency.toFixed(2) +
        ' \u00b7 topic ' + w.topic.toFixed(2) +
        ' \u00b7 source ' + w.source.toFixed(2) +
        ' \u00b7 kind ' + w.kind.toFixed(2) +
        ' \u00b7 novelty ' + w.novelty.toFixed(2) +
        ' \u00b7 prior ' + w.prior.toFixed(2)));
    }

    function highlight(group, key) {
      var rows = panel.querySelectorAll('[data-frk-group]');
      for (var i = 0; i < rows.length; i++) {
        if (rows[i].getAttribute('data-frk-group') === group &&
            rows[i].getAttribute('data-frk-key') === key) {
          if (rows[i].scrollIntoView) rows[i].scrollIntoView({ block: 'nearest' });
          rows[i].classList.add('frk-flash');
          (function (row) {
            setTimeout(function () { row.classList.remove('frk-flash'); }, 1200);
          })(rows[i]);
          return;
        }
      }
    }

    function clearWhy() {
      whyNodes.forEach(function (n) {
        var d = n.getDetail();
        if (d && d.parentNode) d.parentNode.removeChild(d);
        if (n.btn && n.btn.parentNode) n.btn.parentNode.removeChild(n.btn);
      });
      whyNodes = [];
    }

    function renderWhy() {
      clearWhy();
      var items = [];
      try { items = cfg.getItems() || []; } catch (e) {}
      items.forEach(function (entry) {
        var b = el('button', 'frk-why', 'why ranked');
        b.type = 'button';
        b.setAttribute('aria-expanded', 'false');
        b.setAttribute('aria-label', 'Why this is ranked here');
        var detail = null;
        b.addEventListener('click', function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          if (detail) {
            if (detail.parentNode) detail.parentNode.removeChild(detail);
            detail = null;
            b.setAttribute('aria-expanded', 'false');
            return;
          }
          detail = el('div', 'frk-why-detail');
          var ex = [];
          try { ex = FeedRanker.ranker.explain(entry.item) || []; } catch (e) {}
          if (!ex.length) {
            detail.appendChild(el('div', 'frk-why-none', 'No learned signals yet.'));
          }
          ex.forEach(function (sig) {
            var line = el('button', 'frk-why-line',
              sig.group + ' \u00b7 ' + sig.key + ' \u00b7 ' + fmtVal(sig.value));
            line.type = 'button';
            line.addEventListener('click', function (ev2) {
              ev2.stopPropagation();
              setOpen(true);
              highlight(sig.group, sig.key);
            });
            detail.appendChild(line);
          });
          // The page decides placement; default is right after the button.
          if (entry.el && entry.el.parentNode) {
            entry.el.parentNode.insertBefore(detail, entry.el.nextSibling);
          } else {
            b.parentNode.insertBefore(detail, b.nextSibling);
          }
          b.setAttribute('aria-expanded', 'true');
        });
        try { cfg.placeWhy(entry, b); } catch (e) {}
        whyNodes.push({ btn: b, getDetail: function () { return detail; } });
      });
    }

    function syncButton() {
      var foryou = false;
      try { foryou = cfg.getMode() === 'foryou'; } catch (e) {}
      btn.hidden = !foryou;
      var paused = false;
      try { paused = FeedRanker.profile.isPaused(); } catch (e) {}
      btn.textContent = paused ? 'CONSOLE \u00b7 PAUSED' : 'CONSOLE';
      if (!foryou && open) setOpen(false);
    }

    function sync() {
      var foryou = false;
      try { foryou = cfg.getMode() === 'foryou'; } catch (e) {}
      syncButton();
      if (foryou) {
        renderWhy();
        if (open) render();
      } else {
        clearWhy();
      }
    }

    return {
      sync: sync,
      open: function () { setOpen(true); },
      close: function () { setOpen(false); },
      refresh: function () {
        syncButton();
        if (open) {
          // Do not rebuild rows while the reader is interacting with
          // the panel: the slider handler already updates its own row
          // in place, and a rebuild would destroy the drag.
          var ae = null;
          try { ae = document.activeElement; } catch (e) {}
          if (ae && panel.contains(ae)) return;
          render();
        }
      },
      destroy: function () {
        clearWhy();
        if (btn.parentNode) btn.parentNode.removeChild(btn);
        if (panel.parentNode) panel.parentNode.removeChild(panel);
      }
    };
  }

  FeedRanker.console = { mount: mount };
})(typeof window !== 'undefined' ? window : globalThis);
