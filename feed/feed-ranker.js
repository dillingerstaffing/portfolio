/* feed-ranker: order feed items by predicted relevance to the reader.
   Runs in the browser. No server. No tracking. No network calls. */
(function (root) {
'use strict';
var FeedRanker = {};
/* feed-ranker: feature extraction. Item -> feature vector. */
(function (ns) {
  'use strict';

  var MS_PER_HOUR = 3600000;

  function clamp01(x) {
    return x < 0 ? 0 : x > 1 ? 1 : x;
  }

  function recency(item, nowMs, halfLifeHours) {
    var ageHours = Math.max(0, (nowMs - item.publishedAt) / MS_PER_HOUR);
    return Math.exp(-ageHours / halfLifeHours);
  }

  function meanAffinity(values) {
    if (!values.length) return 0;
    var sum = 0;
    for (var i = 0; i < values.length; i++) sum += values[i];
    return sum / values.length;
  }

  // novelty: 1 when the item has not been seen, lower once it has.
  function novelty(item, profile) {
    var state = profile.seen[item.id];
    if (state === 'skipped') return 0.3;
    if (state === 'read') return 0.6;
    return 1;
  }

  // profile: { topicAffinity, sourceAffinity, kindAffinity, seen }
  function extract(item, profile, opts) {
    opts = opts || {};
    var halfLife = opts.halfLifeHours || profile.halfLifeHours || 72;
    var now = opts.nowMs || Date.now();
    var topics = item.topics || [];
    var topicVals = [];
    for (var i = 0; i < topics.length; i++) {
      topicVals.push(profile.topicAffinity[topics[i]] || 0);
    }
    return {
      recency: recency(item, now, halfLife),
      topic: meanAffinity(topicVals),
      source: profile.sourceAffinity[item.source] || 0,
      kind: profile.kindAffinity[item.kind] || 0,
      novelty: novelty(item, profile),
      prior: clamp01((item.signal || 0) / 5)
    };
  }

  ns.features = { extract: extract, recency: recency, novelty: novelty };
})(FeedRanker);
/* feed-ranker: profile load/save. Affinity tables and blend weights,
   persisted in localStorage. Falls back to memory when storage is
   unavailable (private mode, non-browser runtimes). */
(function (ns) {
  'use strict';

  var KEY = 'feed-ranker/profile/v1';

  var DEFAULT_WEIGHTS = {
    recency: 0.25,
    topic: 0.25,
    source: 0.15,
    kind: 0.10,
    novelty: 0.10,
    prior: 0.15
  };

  var memory = {};

  function storage() {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.getItem(KEY);
        return localStorage;
      }
    } catch (e) { /* fall through to memory */ }
    return {
      getItem: function (k) {
        return Object.prototype.hasOwnProperty.call(memory, k) ? memory[k] : null;
      },
      setItem: function (k, v) { memory[k] = String(v); },
      removeItem: function (k) { delete memory[k]; }
    };
  }

  function blank() {
    return {
      version: 1,
      weights: {
        recency: DEFAULT_WEIGHTS.recency,
        topic: DEFAULT_WEIGHTS.topic,
        source: DEFAULT_WEIGHTS.source,
        kind: DEFAULT_WEIGHTS.kind,
        novelty: DEFAULT_WEIGHTS.novelty,
        prior: DEFAULT_WEIGHTS.prior
      },
      halfLifeHours: 72,
      maxAgeDays: 90,
      diversity: { decay: 0.5, floor: 0.2 },
      learningRate: 0.1,
      topicAffinity: {},
      sourceAffinity: {},
      kindAffinity: {},
      seen: {},
      updatedAt: 0
    };
  }

  function load() {
    var p = blank();
    try {
      var raw = storage().getItem(KEY);
      if (raw) {
        var saved = JSON.parse(raw);
        if (saved && saved.version === 1) {
          for (var k in p) {
            if (Object.prototype.hasOwnProperty.call(saved, k)) p[k] = saved[k];
          }
          p.weights = {};
          for (var w in DEFAULT_WEIGHTS) {
            p.weights[w] = (saved.weights && typeof saved.weights[w] === 'number')
              ? saved.weights[w] : DEFAULT_WEIGHTS[w];
          }
          p.topicAffinity = saved.topicAffinity || {};
          p.sourceAffinity = saved.sourceAffinity || {};
          p.kindAffinity = saved.kindAffinity || {};
          p.seen = saved.seen || {};
        }
      }
    } catch (e) { /* corrupted or unreadable: return blank */ }
    return p;
  }

  function save(p) {
    p.updatedAt = Date.now();
    try {
      storage().setItem(KEY, JSON.stringify(p));
    } catch (e) { /* storage full or blocked: keep in-memory state */ }
  }

  function reset() {
    try {
      storage().removeItem(KEY);
    } catch (e) { /* ignore */ }
  }

  ns.profile = {
    load: load,
    save: save,
    reset: reset,
    blank: blank,
    KEY: KEY,
    defaultWeights: function () {
      var w = {};
      for (var k in DEFAULT_WEIGHTS) w[k] = DEFAULT_WEIGHTS[k];
      return w;
    }
  };
})(FeedRanker);
/* feed-ranker: reader feedback. Bounded moving-average updates to the
   affinity tables. Every number that changes has a name (a topic, a
   source, a kind) and a readable value. */
(function (ns) {
  'use strict';

  function clampAffinity(a) {
    return a < -1 ? -1 : a > 1 ? 1 : a;
  }

  function moveToward(table, key, target, step) {
    var cur = table[key] || 0;
    table[key] = clampAffinity(cur + step * (target - cur));
  }

  function touchAffinities(profile, item, target, step) {
    var topics = item.topics || [];
    for (var i = 0; i < topics.length; i++) {
      moveToward(profile.topicAffinity, topics[i], target, step);
    }
    if (item.source) moveToward(profile.sourceAffinity, item.source, target, step);
    if (item.kind) moveToward(profile.kindAffinity, item.kind, target, step);
  }

  // Read: affinity moves toward 1 at the full learning rate.
  function recordRead(item) {
    var p = ns.profile.load();
    var lr = p.learningRate || 0.1;
    touchAffinities(p, item, 1, lr);
    p.seen[item.id] = 'read';
    ns.profile.save(p);
    return p;
  }

  // Skip: affinity moves toward 0 with a smaller step.
  function recordSkip(item) {
    var p = ns.profile.load();
    var lr = p.learningRate || 0.1;
    touchAffinities(p, item, 0, lr * 0.5);
    p.seen[item.id] = 'skipped';
    ns.profile.save(p);
    return p;
  }

  // Dismiss: affinity moves toward -1, and the rules stage excludes
  // the item from future rankings.
  function recordDismiss(item) {
    var p = ns.profile.load();
    var lr = p.learningRate || 0.1;
    touchAffinities(p, item, -1, lr);
    p.seen[item.id] = 'dismissed';
    ns.profile.save(p);
    return p;
  }

  ns.feedback = {
    recordRead: recordRead,
    recordSkip: recordSkip,
    recordDismiss: recordDismiss
  };
})(FeedRanker);
/* feed-ranker: the pipeline. Rules -> features -> score -> diversity
   -> ordered list. Entry point: rank(items). */
(function (ns) {
  'use strict';

  var MS_PER_DAY = 86400000;

  // Rules, applied before scoring, in order:
  // 1. drop items the reader dismissed
  // 2. drop duplicate urls (keep the first occurrence)
  // 3. drop items older than maxAgeDays
  function applyRules(items, profile, opts) {
    opts = opts || {};
    var now = opts.nowMs || Date.now();
    var maxAgeMs = (profile.maxAgeDays || 90) * MS_PER_DAY;
    var out = [];
    var seenUrls = {};
    for (var i = 0; i < items.length; i++) {
      var it = items[i];
      if (profile.seen[it.id] === 'dismissed') continue;
      if (seenUrls[it.url]) continue;
      seenUrls[it.url] = true;
      if (now - it.publishedAt > maxAgeMs) continue;
      out.push(it);
    }
    return out;
  }

  function score(item, profile, opts) {
    var f = ns.features.extract(item, profile, opts);
    var w = profile.weights;
    return w.recency * f.recency +
           w.topic * f.topic +
           w.source * f.source +
           w.kind * f.kind +
           w.novelty * f.novelty +
           w.prior * f.prior;
  }

  // Diversity adjustment: sort by base score descending, then walk the
  // order. For each item, k is the number of already placed items
  // sharing its primary topic. For base >= 0:
  //   final = base * ((1 - floor) * decay^k + floor)
  // This keeps one topic from filling consecutive slots while still
  // letting strong items rise.
  function diversify(scored, profile) {
    var div = profile.diversity || { decay: 0.5, floor: 0.2 };
    var topicCount = {};
    var out = [];
    for (var i = 0; i < scored.length; i++) {
      var it = scored[i].item;
      var base = scored[i].base;
      var primary = (it.topics && it.topics[0]) || '';
      var k = topicCount[primary] || 0;
      var finalScore = base;
      if (base >= 0) {
        finalScore = base * ((1 - div.floor) * Math.pow(div.decay, k) + div.floor);
      }
      topicCount[primary] = k + 1;
      out.push({ item: it, base: base, score: finalScore });
    }
    out.sort(function (a, b) { return b.score - a.score; });
    return out;
  }

  function rank(items, opts) {
    opts = opts || {};
    var profile = ns.profile.load();
    var kept = applyRules(items, profile, opts);
    var scored = [];
    for (var i = 0; i < kept.length; i++) {
      scored.push({ item: kept[i], base: score(kept[i], profile, opts) });
    }
    scored.sort(function (a, b) { return b.base - a.base; });
    var final = diversify(scored, profile);
    var out = [];
    for (var j = 0; j < final.length; j++) out.push(final[j].item);
    return out;
  }

  ns.ranker = {
    rank: rank,
    score: score,
    applyRules: applyRules,
    diversify: diversify
  };
  ns.rank = rank;
})(FeedRanker);
/* feed-ranker: blog support. Adapts portfolio blog articles to rankable
   items. Article topics are mapped onto the same topic vocabulary the
   wire uses, so one shared profile serves both pages: a read on the wire
   raises affinities the blog ranking also sees, and vice versa. The
   profile storage key is unchanged; nothing about the profile forks. */
(function (ns) {
  'use strict';

  var SOURCE = 'portfolio';
  var KIND = 'post';

  // Ordered rules: first matching topic becomes the primary topic, so
  // put the most specific subjects first. Vocabulary matches the wire;
  // 'algorithm' is added for pure-computation notes the wire never
  // carries (checksums, adders, digit encodings).
  var RULES = [
    { topic: 'kernel',
      re: /\bxv6\b|kernel|syscall|scheduler|\bprocess\b|\bpipe\b|page table|paging|context switch|trap handler|supervisor|interrupt handler|user space/ },
    { topic: 'embedded',
      re: /gpio|\bspi\b|\bi2c\b|\bpwm\b|\badc\b|\bdac\b|esp32|stm32|arduino|microcontroller|dev board|poll loop|memory-mapped/ },
    { topic: 'hardware-hacking',
      re: /solder|\bpcb\b|oscilloscope|multimeter|logic analyzer|decap|\bjtag\b|\bbench\b/ },
    { topic: 'riscv-hardware',
      re: /\bfpga\b|\basic\b|\bsoc\b|development board|tapeout/ },
    { topic: 'tooling',
      re: /\blink(er|ing)?\b|\bgcc\b|toolchain|\bgdb\b|\bqemu\b|makefile|compiler|assembler|objdump|disassembly/ },
    { topic: 'algorithm',
      re: /checksum|one'?s-complement|\bbcd\b|\bcrc\b|\bhash\b|double-dabble|\bdigit\b|djb2/ },
    { topic: 'riscv-isa',
      re: /risc-?v\b|instruction|\bcsrr?[swc]?\b|register|opcode|\bisa\b|privileged|unprivileged|\bhart\b/ }
  ];

  function textOf(article) {
    var parts = [article.title || '', article.description || ''];
    var ps = article.paragraphs || [];
    for (var i = 0; i < ps.length && i < 3; i++) parts.push(ps[i]);
    return parts.join('\n').toLowerCase();
  }

  // Returns 1-3 topics from the shared vocabulary. Falls back to
  // riscv-isa: the blog's subject is RISC-V first, so an unrecognized
  // note is more likely about the ISA than about anything else.
  function topicsFor(article) {
    var text = textOf(article);
    var topics = [];
    for (var i = 0; i < RULES.length; i++) {
      if (RULES[i].re.test(text)) topics.push(RULES[i].topic);
      if (topics.length >= 3) break;
    }
    if (!topics.length) topics.push('riscv-isa');
    return topics;
  }

  // Article shape (from data/articles.json): { slug, title, date
  // ("YYYY-MM-DD"), description, paragraphs }. Output is a rankable
  // item: { id, url, title, topics, source, kind, publishedAt, signal }.
  // Articles carry no signal score, so prior starts at 0 and cold start
  // orders by recency, the same as the listing's newest-first default.
  function adapt(article) {
    return {
      id: 'blog:' + article.slug,
      url: '/portfolio/blog/' + article.slug + '/',
      title: article.title,
      topics: topicsFor(article),
      source: SOURCE,
      kind: KIND,
      publishedAt: Date.parse(article.date + 'T00:00:00Z'),
      signal: 0
    };
  }

  function adaptAll(articles) {
    var out = [];
    for (var i = 0; i < articles.length; i++) out.push(adapt(articles[i]));
    return out;
  }

  ns.blog = {
    adapt: adapt,
    adaptAll: adaptAll,
    topicsFor: topicsFor,
    SOURCE: SOURCE,
    KIND: KIND
  };
})(FeedRanker);
/* feed-ranker: dwell-gated reads. A click alone is not a read; only
   sustained attention counts. Two pieces:

   1. track(item, opts): watches one item while its page is open.
      Accumulates only the time the tab is actually visible (hidden time
      never accrues). When accrued visible time reaches thresholdMs
      (default 15000), records a read through onRead (default
      feedback.recordRead) exactly once. Returns { cancel(), accrued() }.

   2. absenceResult(departedAtMs, returnedAtMs, bounceMs): pure bounce
      decision for outbound links. The page notes the departure time when
      the reader clicks out and checks it when the tab becomes visible
      again. Away for bounceMs (default 10000) or longer counts as a
      read; a shorter absence is a bounce and records nothing; no
      departure on record means 'none'. */
(function (ns) {
  'use strict';

  function track(item, opts) {
    opts = opts || {};
    var thresholdMs = typeof opts.thresholdMs === 'number' ? opts.thresholdMs : 15000;
    var onRead = opts.onRead || function (it) { ns.feedback.recordRead(it); };
    var now = opts.now || function () { return Date.now(); };
    var setT = opts.setTimeout || function (fn, ms) { return setTimeout(fn, ms); };
    var clearT = opts.clearTimeout || function (id) { clearTimeout(id); };
    var doc = opts.document || (typeof document !== 'undefined' ? document : null);
    var visibleFn = opts.isVisible || null;

    var accrued = 0;
    var visibleSince = null;
    var timer = null;
    var done = false;
    var unsub = null;

    function isVisible() {
      if (visibleFn) return visibleFn();
      if (doc && typeof doc.visibilityState === 'string') return doc.visibilityState === 'visible';
      return true;
    }
    // Fold the current visible stretch into accrued.
    function settle() {
      if (visibleSince !== null) {
        accrued += Math.max(0, now() - visibleSince);
        visibleSince = null;
      }
    }
    function clearTimer() {
      if (timer !== null) { clearT(timer); timer = null; }
    }
    function finish() {
      if (done) return;
      done = true;
      clearTimer();
      if (unsub) { unsub(); unsub = null; }
      onRead(item);
    }
    function arm() {
      clearTimer();
      if (done || visibleSince === null) return;
      var remaining = thresholdMs - accrued - (now() - visibleSince);
      if (remaining <= 0) { settle(); finish(); return; }
      timer = setT(function () {
        timer = null;
        settle();
        if (accrued >= thresholdMs) { finish(); return; }
        // Timer fired early (throttled while hidden): resume only if visible.
        if (isVisible()) { visibleSince = now(); arm(); }
      }, remaining);
    }
    function onVisibility() {
      if (done) return;
      if (isVisible()) {
        if (visibleSince === null) { visibleSince = now(); arm(); }
      } else {
        settle();
        clearTimer();
      }
    }

    if (isVisible()) { visibleSince = now(); arm(); }
    if (doc && doc.addEventListener && !visibleFn) {
      var handler = onVisibility;
      doc.addEventListener('visibilitychange', handler);
      unsub = function () { doc.removeEventListener('visibilitychange', handler); };
    }

    return {
      // Stop tracking without recording. A quick open-and-back is a
      // bounce: the reader never stayed, so nothing is learned.
      cancel: function () {
        if (done) return;
        done = true;
        clearTimer();
        if (unsub) { unsub(); unsub = null; }
      },
      accrued: function () {
        return accrued + (visibleSince !== null ? Math.max(0, now() - visibleSince) : 0);
      }
    };
  }

  function absenceResult(departedAtMs, returnedAtMs, bounceMs) {
    if (departedAtMs === null || departedAtMs === undefined) return 'none';
    var bounce = typeof bounceMs === 'number' ? bounceMs : 10000;
    var away = (returnedAtMs || Date.now()) - departedAtMs;
    return away >= bounce ? 'read' : 'bounce';
  }

  ns.dwell = {
    track: track,
    absenceResult: absenceResult
  };
})(FeedRanker);
root.FeedRanker = FeedRanker;
})(typeof window !== 'undefined' ? window : globalThis);
