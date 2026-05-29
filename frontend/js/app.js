/* ═══════════ BrianRAG — Application JS ═══════════ */
gsap.registerPlugin(ScrollTrigger);
const $ = s => document.querySelector(s), $$ = s => document.querySelectorAll(s);
const M = /iPhone|iPad|Android/i.test(navigator.userAgent);
let SCROLL = 0;

/* ═══════════ Lenis Smooth Scroll ═══════════ */
const lenis = new Lenis({
  duration: 1.2,
  easing: t => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
  smoothWheel: true,
  smoothTouch: false
});
function raf(time) { lenis.raf(time); requestAnimationFrame(raf); }
requestAnimationFrame(raf);
lenis.on('scroll', ({ scroll }) => { SCROLL = scroll; ScrollTrigger.update(); });

/* ═══════════ Cursor ═══════════ */
const cursor = $('#cursor');
let cx = 0, cy = 0;
document.addEventListener('mousemove', e => {
  cx = e.clientX; cy = e.clientY;
  cursor.style.opacity = '1';
  cursor.style.left = cx + 'px';
  cursor.style.top = cy + 'px';
});
document.addEventListener('mouseleave', () => { cursor.style.opacity = '0'; });
$$('a,button,.cr,.quick-q,.si,.bc,.tilt-card,.fw,.mb,.ra-tab,.doc-row .del,.upz,.pixel-card,[onclick]').forEach(el => {
  el.addEventListener('mouseenter', () => cursor.classList.add('hover'));
  el.addEventListener('mouseleave', () => cursor.classList.remove('hover'));
});

/* ═══════════ Iridescence Shader ═══════════ */
(function () {
  const cv = document.getElementById('iridescence-canvas');
  const r = new THREE.WebGLRenderer({ canvas: cv, alpha: true, antialias: false });
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  const s = new THREE.Scene(), c = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const m = new THREE.ShaderMaterial({
    fragmentShader: `precision highp float;
uniform float uT;uniform vec3 uC;uniform vec3 uR;uniform vec2 uM;uniform float uA;uniform float uS;
varying vec2 vUv;
void main(){float mr=min(uR.x,uR.y);vec2 uv=(vUv*2.-1.)*uR.xy/mr;uv+=(uM-.5)*uA;float d=-uT*.5*uS,a=0.;for(float i=0.;i<8.;++i){a+=cos(i-d-a*uv.x);d+=sin(uv.y*i+a);}d+=uT*.5*uS;vec3 col=vec3(cos(uv*vec2(d,a))*.6+.4,cos(a+d)*.5+.5);col=cos(col*cos(vec3(d,a,2.5))*.5+.5)*uC;gl_FragColor=vec4(col,1.);}`,
    vertexShader: 'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.,1.);}',
    uniforms: {
      uT: { value: 0 }, uC: { value: new THREE.Vector3(.4, .3, .5) },
      uR: { value: new THREE.Vector3(1, 1, 1) }, uM: { value: new THREE.Vector2(.5, .5) },
      uA: { value: .06 }, uS: { value: .5 }
    }, transparent: true, depthWrite: false
  });
  s.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), m));
  function rs() {
    const w = innerWidth, h = innerHeight;
    r.setSize(w, h); m.uniforms.uR.value.set(w, h, w / h);
  }
  window.addEventListener('resize', rs); rs();
  function anim(t) {
    requestAnimationFrame(anim);
    const sc = SCROLL / 3000;
    m.uniforms.uT.value = t * .001;
    m.uniforms.uM.value.set(.5, Math.min(.5 + sc * .12, .72));
    m.uniforms.uC.value.set(.32 + sc * .12, .25 + sc * .08, .44 + Math.sin(sc * .7) * .08 + Math.cos(sc * .4) * .04);
    r.render(s, c);
  }
  requestAnimationFrame(anim);
})();

/* ═══════════ 3D Scene ═══════════ */
(function () {
  const cv = document.getElementById('scene-canvas');
  const r = new THREE.WebGLRenderer({ canvas: cv, alpha: true, antialias: !M });
  r.setPixelRatio(Math.min(devicePixelRatio, 2));
  const s = new THREE.Scene();
  const c = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, .1, 180);
  c.position.set(0, 10, 32); c.lookAt(0, -2, 0);
  s.add(new THREE.AmbientLight(0x1a1a35, .65));
  const kl = new THREE.PointLight(0xd4c098, 90, 65);
  kl.position.set(10, 8, 15); s.add(kl);
  for (let h = 0; h < 5; h++) {
    const ri = new THREE.Mesh(new THREE.TorusGeometry(4 + h * 3, .012, 8, 140),
      new THREE.MeshBasicMaterial({ color: 0xd4c098, transparent: true, opacity: .07 + .03 * h }));
    ri.rotation.x = Math.PI / 2; ri.position.y = -12 + h * 2; s.add(ri);
  }
  const shapes = [];
  const geos = [new THREE.IcosahedronGeometry(.5, 1), new THREE.TorusKnotGeometry(.35, .09, 64, 8, 2, 3),
    new THREE.OctahedronGeometry(.4, 0), new THREE.TetrahedronGeometry(.4, 0),
    new THREE.DodecahedronGeometry(.35, 0), new THREE.TorusGeometry(.35, .07, 12, 28)];
  const wMat = new THREE.MeshStandardMaterial({ color: 0xd8ccaa, wireframe: true, roughness: .35, metalness: .95, transparent: true, opacity: .2 });
  const sMat = new THREE.MeshStandardMaterial({ color: 0x1c1c38, roughness: .2, metalness: .75, transparent: true, opacity: .5 });
  for (let i = 0; i < 50; i++) {
    const geo = geos[i % geos.length];
    const mesh = new THREE.Mesh(geo, i % 3 === 0 ? wMat : sMat);
    const a = (i / 50) * Math.PI * 4, rad = 4 + (i / 50) * 14, ht = -12 + (i / 50) * 10;
    mesh.position.set(Math.cos(a) * rad, ht, Math.sin(a) * rad - Math.sin(i * .5) * 3);
    mesh.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, Math.random() * Math.PI);
    mesh.userData = { rx: .001 + Math.random() * .006, ry: .002 + Math.random() * .008, rz: .0005 + Math.random() * .004,
      baseY: mesh.position.y, fa: .2 + Math.random() * 1.5, ff: .3 + Math.random() * .5 };
    shapes.push(mesh); s.add(mesh);
  }
  const dust = new THREE.Points(new THREE.BufferGeometry(),
    new THREE.PointsMaterial({ color: 0xd8ccaa, size: .028, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: .14 }));
  const dc = M ? 1500 : 6000;
  const dp = new Float32Array(dc * 3);
  for (let i = 0; i < dc; i++) { dp[i * 3] = (Math.random() - .5) * 50; dp[i * 3 + 1] = Math.random() * 30 - 15; dp[i * 3 + 2] = (Math.random() - .5) * 40; }
  dust.geometry.setAttribute('position', new THREE.BufferAttribute(dp, 3)); s.add(dust);
  function rs() { r.setSize(innerWidth, innerHeight); c.aspect = innerWidth / innerHeight; c.updateProjectionMatrix(); }
  window.addEventListener('resize', rs); rs();
  const clk = new THREE.Clock();
  function anim() {
    requestAnimationFrame(anim);
    const t = clk.getElapsedTime(), sc = SCROLL / 1000;
    const camZ = 32 - sc * 7;
    const camY = 10 + sc * 8;
    const camX = Math.sin(sc * .18) * 6;
    c.position.lerp(new THREE.Vector3(camX, Math.min(camY, 38), Math.max(camZ, 5)), .025);
    const lx = Math.cos(sc * .15) * 3, ly = -2 + sc * 3, lz = sc * 2.5;
    c.lookAt(lx, Math.min(ly, 28), lz);
    shapes.forEach(sh => {
      sh.rotation.x += sh.userData.rx; sh.rotation.y += sh.userData.ry; sh.rotation.z += sh.userData.rz;
      sh.position.y = sh.userData.baseY + Math.sin(t * sh.userData.ff) * sh.userData.fa + sc * sh.userData.fa * 1.2;
    });
    const dp2 = dust.geometry.attributes.position.array;
    for (let i = 0; i < Math.min(dc, dp2.length / 3); i += 3) { dp2[i + 1] -= .015; if (dp2[i + 1] < -15) dp2[i + 1] = 15; }
    dust.geometry.attributes.position.needsUpdate = true;
    kl.intensity = 80 + Math.sin(t * .4) * 20; r.render(s, c);
  }
  requestAnimationFrame(anim);
})();

/* ═══════════ Glow Parallax ═══════════ */
lenis.on('scroll', ({ scroll }) => {
  const s = scroll / 1000;
  $$('.glow').forEach((o, i) => {
    o.style.transform = `translateY(${s * (40 + i * 25)}px) translateX(${Math.sin(s * .3 + i) * 50}px)`;
    o.style.opacity = .5 + Math.sin(s * .2 + i) * .2;
  });
});

/* ═══════════ Camera Scroll Engine ═══════════ */
let _statsTriggered = false, _bounceTriggered = false, _prevActiveIdx = -1;

const SECTION_DEFS = [
  { id: 'hero', idx: 0, z: 0, rx: 0 },
  { id: 'vel-sec', idx: 1, z: -80, rx: 0 },
  { id: 'stats-sec', idx: 2, z: 30, rx: -3 },
  { id: 'focus-sec', idx: 3, z: -50, rx: 2 },
  { id: 'feat-sec', idx: 4, z: 0, rx: -2 },
  { id: 'px-sec', idx: 5, z: -60, rx: 3 },
  { id: 'bounce-sec', idx: 6, z: 40, rx: 0 },
  { id: 'cta-sec', idx: 7, z: 0, rx: 0 },
];
const ZONE_H = () => innerHeight * 1.30;

const easeOutCubic = t => 1 - Math.pow(1 - t, 3);
const easeInOutCubic = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

function update3DTransforms() {
  const sc = SCROLL, zh = ZONE_H();
  SECTION_DEFS.forEach((def, i) => {
    const el = document.getElementById(def.id);
    if (!el) return;
    const zs = def.idx * zh, lp = (sc - zs) / zh;
    let opacity, ty, scale, tz, rx;
    if (lp < -0.28) { opacity = 0; ty = 90; scale = 0.86; tz = def.z; rx = def.rx + 6; }
    else if (lp < 0) {
      const t = (lp + 0.28) / 0.28, e = easeOutCubic(t);
      opacity = e; ty = 90 * (1 - e); scale = 0.86 + 0.14 * e;
      tz = def.z * (1 - e); rx = (def.rx + 6) * (1 - e) + def.rx * e;
    }
    else if (lp < 0.65) {
      const t = lp / 0.65;
      opacity = 1; ty = Math.sin(t * Math.PI) * -5; scale = 1 + Math.sin(t * Math.PI) * 0.008;
      tz = 0; rx = def.rx + Math.sin(t * Math.PI * 2) * 0.6;
    }
    else if (lp < 1.0) {
      const t = (lp - 0.65) / 0.35, e = t * t * t;
      opacity = 1 - e; ty = -70 * e; scale = 1 - 0.07 * e;
      tz = -def.z * e; rx = def.rx - 5 * e;
    }
    else { opacity = 0; ty = -70; scale = 0.93; tz = -def.z; rx = def.rx - 5; }
    el.style.opacity = opacity;
    el.style.transform = `translateY(${ty}px) translateZ(${tz}px) scale(${scale}) rotateX(${rx}deg)`;
    el.style.pointerEvents = opacity > 0.25 ? 'auto' : 'none';
  });
  // progress dots
  const activeIdx = Math.round(sc / zh);
  if (activeIdx !== _prevActiveIdx) {
    _prevActiveIdx = activeIdx;
    $$('#scene-dots .dot').forEach((d, i) => {
      d.classList.remove('active', 'passed');
      if (i === activeIdx) d.classList.add('active');
      else if (i < activeIdx) d.classList.add('passed');
    });
    const vig = document.getElementById('vignette');
    if (vig && activeIdx > 0) {
      vig.classList.add('on');
      clearTimeout(vig._timeout);
      vig._timeout = setTimeout(() => vig.classList.remove('on'), 500);
    }
  }
  _animateChildren(sc, zh);
}

$$('#scene-dots .dot').forEach(d => {
  d.addEventListener('click', () => {
    const idx = parseInt(d.dataset.idx);
    lenis.scrollTo(idx * ZONE_H(), { duration: 1.2, easing: t => 1 - Math.pow(1 - t, 3) });
  });
});

document.addEventListener('keydown', e => {
  if (document.activeElement && document.activeElement.tagName === 'TEXTAREA') return;
  if ($('#rag-app')?.classList.contains('open')) return;
  const zh = ZONE_H(), curIdx = Math.round(SCROLL / zh);
  if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
    e.preventDefault();
    lenis.scrollTo(Math.min(curIdx + 1, 7) * zh, { duration: 1, easing: t => 1 - Math.pow(1 - t, 3) });
  } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
    e.preventDefault();
    lenis.scrollTo(Math.max(curIdx - 1, 0) * zh, { duration: 1, easing: t => 1 - Math.pow(1 - t, 3) });
  }
});

function _setStyle(id, props) {
  const el = document.getElementById(id);
  if (!el) return;
  for (const [k, v] of Object.entries(props)) el.style[k] = v;
}

function _animateChildren(sc, zh) {
  const statsLP = (sc - 2 * zh) / zh;
  if (!_statsTriggered && statsLP > 0) {
    _statsTriggered = true;
    gsap.fromTo('#stats-lbl', { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 1, ease: 'power3.out' });
    [['#st1', 0], ['#st2', 200], ['#st3', 400]].forEach(([id, delay]) => {
      setTimeout(() => {
        const el = $(id + ' .stat-num'); if (!el) return;
        const to = parseFloat(el.dataset.countup), dur = 1800, st = performance.now();
        function up(t) { const p = Math.min(Math.max((t - st) / dur, 0), 1), ed = 1 - Math.pow(1 - p, 3); el.textContent = Math.round(ed * to); if (p < 1) requestAnimationFrame(up); else el.textContent = to; }
        requestAnimationFrame(up);
      }, delay);
    });
  }
  const featLP = (sc - 4 * zh) / zh;
  if (featLP > -0.28 && featLP < 0.25) {
    const t = Math.min(Math.max((featLP + 0.28) / 0.40, 0), 1), e = easeOutCubic(t);
    _setStyle('feat1', { transform: `translateX(${Math.max(-400 * (1 - e), 0)}px) rotateY(${20 * (1 - e)}deg)`, opacity: e });
    _setStyle('feat2', { transform: `translateY(${Math.max(160 * (1 - Math.min(e * 1.3, 1)), 0)}px) scale(${0.6 + 0.4 * e})`, opacity: Math.min(e * 1.2, 1) });
    _setStyle('feat3', { transform: `translateX(${Math.min(400 * (1 - e), 400)}px) rotateY(${-20 * (1 - e)}deg)`, opacity: Math.min(e * 1.15, 1) });
  } else if (featLP >= 0.25 && featLP < 0.3) { _setStyle('feat1', { transform: '', opacity: 1 }); _setStyle('feat2', { transform: '', opacity: 1 }); _setStyle('feat3', { transform: '', opacity: 1 }); }
  const pxLP = (sc - 5 * zh) / zh;
  if (pxLP > -0.28 && pxLP < 0.2) {
    const t = Math.min(Math.max((pxLP + 0.28) / 0.35, 0), 1), e = easeOutCubic(t);
    _setStyle('px1', { transform: `translateX(${Math.max(-150 * (1 - e), 0)}px)`, opacity: e });
    _setStyle('px2', { transform: `translateX(${Math.min(150 * (1 - e), 150)}px)`, opacity: Math.min(e * 1.1, 1) });
  } else if (pxLP >= 0.2 && pxLP < 0.25) { _setStyle('px1', { transform: '', opacity: 1 }); _setStyle('px2', { transform: '', opacity: 1 }); }
  const bounceLP = (sc - 6 * zh) / zh;
  if (!_bounceTriggered && bounceLP > -0.05) {
    _bounceTriggered = true;
    $$('.bc').forEach((c, i) => {
      setTimeout(() => {
        c.dataset.ot = c.style.transform;
        c.style.transform = 'scale(0)';
        requestAnimationFrame(() => { c.style.transform = c.dataset.ot; c.style.transition = 'transform .5s cubic-bezier(.34,1.56,.64,1)'; });
      }, i * 60);
    });
  }
  const ctaLP = (sc - 7 * zh) / zh;
  if (ctaLP > -0.28 && ctaLP < 0.3) {
    const t = Math.min(Math.max((ctaLP + 0.28) / 0.40, 0), 1), e = easeOutCubic(t);
    _setStyle('cta-card', { transform: `scale(${0.8 + 0.2 * e}) translateY(${(1 - e) * 30}px)`, opacity: e });
  } else if (ctaLP >= 0.3 && ctaLP < 0.35) { _setStyle('cta-card', { transform: '', opacity: 1 }); }
  const focusLP = (sc - 3 * zh) / zh;
  if (focusLP > -0.15 && focusLP < 0.8) { if (window._focusStart) window._focusStart(); }
  else { if (window._focusStop) window._focusStop(); }
}

lenis.on('scroll', update3DTransforms);
update3DTransforms();

/* ═══════════ HERO Entrance ═══════════ */
const heroTL = gsap.timeline({ defaults: { ease: 'power3.out' } });
heroTL.fromTo('#logo-wrap', { opacity: 0, scale: .3, filter: 'blur(16px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)', duration: 2, ease: 'power2.inOut' }, .1);
heroTL.fromTo('#hero-lbl', { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 1.2 }, .7);
heroTL.fromTo('#hero-title', { opacity: 0, y: 60, scale: .9 }, { opacity: 1, y: 0, scale: 1, duration: 1.4 }, .9);
heroTL.fromTo('#hero-sub', { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 1.2 }, 1.1);
heroTL.fromTo('#hero-btn', { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 1 }, 1.3);

/* ═══════════ Bounce Cards Hover ═══════════ */
$$('.bc').forEach(c => {
  c.addEventListener('mouseenter', function () {
    const cards = $$('.bc'), mi = Array.from(cards).indexOf(this);
    cards.forEach((s, j) => {
      if (s === this) { s.style.transform = (s.dataset.ot || s.style.transform).replace(/rotate\([^)]*\)/, 'rotate(0deg)'); s.style.zIndex = 10; }
      else { const ox = j < mi ? -110 : 110; s.style.transform = (s.dataset.ot || s.style.transform).replace(/translate\(([-\d.]+)px\)/, (m, v) => `translate(${parseFloat(v) + ox}px)`); }
    });
  });
  c.addEventListener('mouseleave', () => { $$('.bc').forEach(s => { s.style.transform = s.dataset.ot; s.style.zIndex = ''; }); });
});

/* ═══════════ Interactive Effects ═══════════ */
$$('[data-pixel]').forEach(card => {
  const cv = document.createElement('canvas');
  cv.style.cssText = 'position:absolute;inset:0;z-index:0;width:100%;height:100%';
  card.style.position = 'relative'; card.style.overflow = 'hidden'; card.appendChild(cv);
  const ctx = cv.getContext('2d'); let pixels = [], animId, isHovering = false;
  function init() {
    const rect = card.getBoundingClientRect(), w = Math.floor(rect.width), h = Math.floor(rect.height);
    cv.width = w; cv.height = h; const gap = 5;
    const colors = ['rgba(212,192,152,.2)', 'rgba(212,192,152,.1)', 'rgba(255,255,255,.06)'];
    pixels = [];
    for (let x = 0; x < w; x += gap) for (let y = 0; y < h; y += gap) {
      const c = colors[Math.floor(Math.random() * colors.length)];
      pixels.push({ x, y, color: c, size: 0, maxSize: 1 + Math.random() * 2.5, speed: .02 + Math.random() * .1, delay: Math.hypot(x - w / 2, y - h / 2) * .015, counter: 0, isIdle: true });
    }
  }
  init(); new ResizeObserver(() => { init(); }).observe(card);
  function draw() { ctx.clearRect(0, 0, cv.width, cv.height); let allIdle = true; for (const p of pixels) { if (p.isIdle) { if (!isHovering) continue; } else allIdle = false; ctx.fillStyle = p.color; const s = p.size || 1; ctx.fillRect(p.x - s * .5, p.y - s * .5, s, s); } return allIdle; }
  function appear() { isHovering = true; pixels.forEach(p => { if (p.counter <= p.delay) { p.counter++; return; } p.isIdle = false; if (p.size < p.maxSize) p.size += p.speed; }); }
  function disappear() { isHovering = false; pixels.forEach(p => { p.counter = 0; if (p.size > 0) { p.size -= .1; p.isIdle = false; } else p.isIdle = true; }); }
  card.addEventListener('mouseenter', () => { cancelAnimationFrame(animId); animId = requestAnimationFrame(function loop() { appear(); draw(); animId = requestAnimationFrame(loop); }); });
  card.addEventListener('mouseleave', () => { cancelAnimationFrame(animId); animId = requestAnimationFrame(function loop() { disappear(); const done = draw(); if (!done) animId = requestAnimationFrame(loop); }); });
});

$$('[data-tilt]').forEach(card => {
  const inner = card.querySelector('.tc'); if (!inner) return;
  card.addEventListener('mousemove', e => {
    const r = card.getBoundingClientRect();
    inner.style.transform = `rotateY(${((e.clientX - r.left) / r.width - .5) * 14}deg) rotateX(${-((e.clientY - r.top) / r.height - .5) * 14}deg)`;
  });
  card.addEventListener('mouseleave', () => { inner.style.transition = 'transform .7s ease-out'; inner.style.transform = 'rotateY(0) rotateX(0)'; });
  card.addEventListener('mouseenter', () => { inner.style.transition = 'transform .1s ease-out'; });
});

$$('[data-spotlight]').forEach(card => {
  card.addEventListener('mousemove', e => {
    const r = card.getBoundingClientRect();
    card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
    card.style.setProperty('--my', (e.clientY - r.top) + 'px');
  });
});

$$('[data-magnet]').forEach(wrap => {
  const inner = wrap.querySelector('.mi'); if (!inner) return;
  document.addEventListener('mousemove', e => {
    const r = wrap.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    if (Math.abs(cx - e.clientX) < r.width / 2 + 120 && Math.abs(cy - e.clientY) < r.height / 2 + 120) {
      inner.style.transform = `translate3d(${(e.clientX - cx) / 5}px,${(e.clientY - cy) / 5}px,0)`;
      inner.style.transition = 'transform .3s ease-out';
    } else { inner.style.transform = 'translate3d(0,0,0)'; inner.style.transition = 'transform .5s ease-in-out'; }
  });
});

(function () {
  const words = $$('#focus-wrap .fw'), frame = $('#focus-frame');
  if (!words.length || !frame) return;
  let idx = 0, timer = null;
  function mv(i) {
    words.forEach((w, j) => { w.style.filter = j === i ? 'blur(0px)' : 'blur(4px)'; w.style.color = j === i ? 'var(--cream)' : 'var(--td)'; });
    const w = words[i];
    frame.style.left = w.offsetLeft + 'px'; frame.style.top = w.offsetTop + 'px';
    frame.style.width = w.offsetWidth + 'px'; frame.style.height = w.offsetHeight + 'px'; frame.style.opacity = '1';
  }
  window._focusStart = () => { if (timer) return; mv(idx); timer = setInterval(() => { idx = (idx + 1) % words.length; mv(idx); }, 2200); };
  window._focusStop = () => { if (timer) { clearInterval(timer); timer = null; } frame.style.opacity = '0'; };
  words.forEach((w, i) => {
    w.addEventListener('mouseenter', () => { if (timer) { clearInterval(timer); timer = null; } idx = i; mv(i); });
    w.addEventListener('mouseleave', () => { window._focusStart(); });
  });
})();

$$('[data-prox]').forEach(el => {
  document.addEventListener('mousemove', e => {
    const r = el.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2,
      f = Math.max(0, 1 - Math.hypot(e.clientX - cx, e.clientY - cy) / 200);
    el.style.fontWeight = 200 + f * 500; el.style.color = f > .5 ? 'var(--gold)' : 'var(--td)';
    el.style.transform = `scale(${1 + f * .08})`;
  });
});

/* ═══════════ Chat App ═══════════ */
if (typeof marked !== 'undefined') {
  marked.setOptions({ breaks: true, gfm: true });
  const renderer = new marked.Renderer();
  const origCode = renderer.code.bind(renderer);
  renderer.code = function ({ text, lang }) { return origCode({ text, lang: lang || '' }); };
  const origText = renderer.text.bind(renderer);
  renderer.text = function (token) { return origText(token); };
  const origParagraph = renderer.paragraph.bind(renderer);
  renderer.paragraph = function (token) { return origParagraph(token); };
  marked.setOptions({ renderer });
}

function renderMD(raw) {
  if (typeof marked === 'undefined') return raw.replace(/\n/g, '<br>');
  let t = raw;
  t = t.replace(/\$\$([\s\S]*?)\$\$/g, (_, f) => renderKaTeX(f, 'block'));
  t = t.replace(/\\\[([\s\S]*?)\\\]/g, (_, f) => renderKaTeX(f, 'block'));
  t = t.replace(/\$(.+?)\$/g, (_, f) => renderKaTeX(f, 'inline'));
  t = t.replace(/\\\((.+?)\\\)/g, (_, f) => renderKaTeX(f, 'inline'));
  let html = marked.parse(t);
  html = html.replace(/\[(\d+)\]/g, (_, n) => `<sup class="cr" onclick="App.showCite(event,'${n}')">[${n}]</sup>`);
  return html;
}

function renderKaTeX(formula, display) {
  try {
    if (typeof renderMathInElement !== 'undefined' || typeof katex !== 'undefined') {
      return katex.renderToString(formula, { throwOnError: false, displayMode: display === 'block' });
    }
  } catch (e) { }
  return display === 'block' ? `<div style="text-align:center;padding:8px 0">\\(${formula}\\)</div>` : `\\(${formula}\\)`;
}

const App = (function () {
  let aMode = 'rag', streaming = false, _cs = {}, _history = [], _abort = null, _lastQuestion = '';

  const friendlyError = e => {
    const m = (e.message || String(e)).toLowerCase();
    if (m.includes('failed to fetch') || m.includes('network')) return '无法连接服务器，请确认服务是否已启动。';
    if (m.includes('timeout') || m.includes('abort')) return '请求已取消或超时。';
    if (m.includes('429') || m.includes('too many')) return '请求太频繁，请稍后再试。';
    if (m.includes('500') || m.includes('internal')) return '服务器内部错误，请稍后重试。';
    return '抱歉，处理请求时出现问题，请重试。';
  };

  function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
  function cS() { const el = $('#achat'); if (el) el.scrollTop = el.scrollHeight; }
  function aM(role, html) { const d = document.createElement('div'); d.className = 'msg-m ' + role; d.innerHTML = `<div class="msg-av">${role === 'you' ? '👤' : '🤖'}</div><div class="msg-bd">${html}</div>`; $('#achat').appendChild(d); return d; }
  function updatePhase(el, text) { let ph = el.querySelector('.phase-indicator'); if (!ph) { ph = document.createElement('div'); ph.className = 'phase-indicator'; ph.innerHTML = '<span class="phase-dot"></span><span class="phase-text"></span>'; el.querySelector('.msg-bd').prepend(ph); } ph.querySelector('.phase-text').textContent = text; }

  // ── Search History ──
  function loadHistory() { try { return JSON.parse(localStorage.getItem('brianrag_history') || '[]'); } catch(e) { return []; } }
  function saveHistory(q) { let h = loadHistory(); h = h.filter(x => x !== q); h.unshift(q); if (h.length > 20) h.pop(); localStorage.setItem('brianrag_history', JSON.stringify(h)); }
  function clearHistory() { localStorage.removeItem('brianrag_history'); }
  function renderHistory() {
    const h = loadHistory(); const qr = $('#quick-row'); if (!qr) return;
    const existing = qr.querySelectorAll('.hist-group'); existing.forEach(e => e.remove());
    if (!h.length) return;
    const g = document.createElement('div'); g.className = 'hist-group';
    g.innerHTML = `<div style="display:flex;align-items:center;justify-content:space-between;margin-top:12px;margin-bottom:4px"><span style="font-size:9px;color:var(--tm);text-transform:uppercase;letter-spacing:.1em">Recent</span><button onclick="App.clearSearchHistory()" style="background:none;border:none;color:var(--td);cursor:pointer;font-size:9px">clear</button></div>` + h.slice(0, 4).map(q => `<button class="quick-q hist-q">${esc(q)}</button>`).join('');
    qr.appendChild(g);
    g.querySelectorAll('.hist-q').forEach(b => b.addEventListener('click', () => { $('#qinput').value = b.textContent; send(); }));
  }

  async function send() {
    if (streaming) { stopStream(); return; }
    const inp = $('#qinput'), q = inp.value.trim(); if (!q) return;
    _lastQuestion = q; inp.value = ''; streaming = true;
    saveHistory(q); renderHistory();
    const btn = $('#sbtn'); btn.disabled = true; btn.classList.add('stop'); btn.textContent = 'Stop';
    const empt = $('#empt'); if (empt) empt.style.display = 'none';
    const um = aM('you', esc(q)); cS();
    const am = aM('ai', '<span style="color:var(--td)">prepare...</span>');
    updatePhase(am, 'searching');
    const hist = []; let _q = null;
    _history.forEach(m => { if (m.role === 'you') _q = m.text; else if (_q && m.answer) { hist.push({ role: 'user', content: _q }); hist.push({ role: 'assistant', content: m.answer }); _q = null; } });
    const histParam = hist.length > 0 ? `&history=${encodeURIComponent(JSON.stringify(hist))}` : '';
    try {
      _abort = new AbortController();
      const resp = await fetch(`/api/query/stream?question=${encodeURIComponent(q)}&mode=${aMode}${histParam}`, { signal: _abort.signal });
      const reader = resp.body.getReader(); const dec = new TextDecoder();
      let buf = '', ans = '', cit = {}, chunks = [], chunkSources = [], st = false; const body = am.querySelector('.msg-bd');
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        buf += dec.decode(value, { stream: !0 }); const lines = buf.split('\n'); buf = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const d = JSON.parse(line.slice(6));
            if (d.phase) { updatePhase(am, d.phase); }
            if (d.token) { if (!st) { body.innerHTML = ''; st = true; updatePhase(am, 'generating'); } ans += d.token; body.innerHTML = renderMD(ans) + '<span class="phase-dot" style="display:inline-block;margin-left:2px;animation:pulse .8s infinite"></span>'; }
            if (d.done) { if (d.citations) cit = d.citations; if (d.used_chunks) chunks = d.used_chunks; if (d.chunk_sources) chunkSources = d.chunk_sources; }
          } catch (e) { }
        }
        cS();
      }
      body.innerHTML = body.innerHTML.replace(/<span class="phase-dot"[^>]*><\/span>/g, '');
      const ph = am.querySelector('.phase-indicator'); if (ph) ph.remove();
      if (ans) fin(am, ans, cit, chunks, chunkSources);
      _history.push({ role: 'you', text: q }); _history.push({ role: 'ai', answer: ans }); if (_history.length > 50) _history.splice(0, 2);
    } catch (e) {
      if (e.name === 'AbortError') { am.querySelector('.msg-bd').innerHTML = '<span style="color:var(--td)">已取消。</span>'; }
      else { am.querySelector('.msg-bd').innerHTML = '<span style="color:#d55">' + friendlyError(e) + '</span>'; }
    }
    streaming = false; _abort = null; btn.disabled = false; btn.classList.remove('stop'); btn.textContent = 'Send'; cS();
  }

  function stopStream() { if (_abort) { _abort.abort(); _abort = null; } }

  function fin(el, ans, cit, chunks, chunkSources) {
    if (cit) { Object.entries(cit).forEach(function (e) { _cs[e[0]] = typeof e[1] === "string" ? { text: e[1] } : e[1]; }); }
    else if (chunks) { chunks.forEach(function (c, i) { _cs[String(i + 1)] = { text: c }; }); }
    el.querySelector(".msg-bd").innerHTML = renderMD(ans);
    var n = Object.keys(cit || {}).length, lb = n >= 3 ? "high" : n === 0 ? "low" : "medium";
    var srcs = chunkSources || [], uf = [], seen = {};
    srcs.forEach(function (s) { var f = s.file; if (f && !seen[f]) { seen[f] = 1; uf.push(f); } });
    var sb = uf.length ? ("<div class=\"src-bar\" style=\"margin-top:10px;padding:6px 10px;background:var(--gh);border-radius:6px;font-size:10px;color:var(--td)\">Based on " + uf.length + " source" + (uf.length > 1 ? "s" : "") + ": " + uf.slice(0, 5).map(function (f) { return "<code style=\"font-size:9px\">" + esc(f) + "</code>"; }).join(", ") + (uf.length > 5 ? ", …" : "") + "</div>") : "";
    var acts = document.createElement("div"); acts.className = "msg-acts";
    acts.innerHTML = sb + "<button onclick=\"App.copyMsg(this)\">copy</button><button onclick=\"App.regenerate()\">retry</button><button onclick=\"App.fb(this,'positive')\">👍</button><button onclick=\"App.fb(this,'negative')\">👎</button><span class=\"cf-badge\">" + lb + " conf</span>";
    el.querySelector(".msg-bd").appendChild(acts);
    var sl = document.getElementById("src-list");
    if (sl) sl.innerHTML = srcs.filter(function (s) { return s.file; }).map(function (s, i) { var c = _cs[String(i + 1)], t = c ? c.text : ""; return "<div class=\"src-item\" onclick=\"App.showChunk(" + (i + 1) + ")\" style=\"margin:6px 0;padding:6px;border-radius:4px;cursor:pointer;border-left:2px solid var(--gm)\"><div style=\"font-size:10px;color:var(--gold)\">[" + (i + 1) + "] " + esc(s.file || "unknown") + "</div><div style=\"font-size:9px;color:var(--td);margin-top:2px\">" + esc((t || "").slice(0, 80)) + (t && t.length > 80 ? "..." : "") + "</div></div>"; }).join("");
  }

  function showChunk(n) { App.switchTab("sources"); setTimeout(function () { var all = document.querySelectorAll("#src-list .src-item"); all.forEach(function (e) { e.style.background = ""; }); var t = all[n - 1]; if (t) { t.style.background = "var(--gh)"; t.scrollIntoView({ behavior: "smooth", block: "center" }); } }, 100); }

  function showCite(e, num) { e.stopPropagation(); var c = _cs[num]; if (!c) return; var pop = document.getElementById("cite-pop"); if (!pop) return; var txt = typeof c === "string" ? c : (c.text || ""); var src = c.source || {}; var file = src.file ? ("<div class=\"src\" style=\"font-size:9px;color:var(--gold)\">" + esc(src.file) + "</div>") : ""; pop.innerHTML = file + "<div class=\"src\">Source [" + num + "]</div>" + esc(txt); pop.classList.add("show"); pop.style.left = Math.min(e.clientX + 12, innerWidth - 380) + "px"; pop.style.top = (e.clientY - 20) + "px"; }
  document.addEventListener("click", function () { var p = document.getElementById("cite-pop"); if (p) p.classList.remove("show"); });

  function copyMsg(el) { const txt = el.closest('.msg-bd').innerText; navigator.clipboard.writeText(txt).then(() => { el.textContent = 'copied'; setTimeout(() => el.textContent = 'copy', 1500); }); }

  async function fb(el, fb) {
    const msg = el.closest('.msg-m'), qEl = msg.previousElementSibling;
    if (!qEl || !qEl.classList.contains('you')) return;
    await fetch('/api/feedback', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question: qEl.querySelector('.msg-bd').textContent, answer: msg.querySelector('.msg-bd').innerText, feedback: fb }) });
    el.classList.add('voted');
  }

  function setMode(m) {
    aMode = m; $$('.mb').forEach(b => b.classList.remove('sel'));
    $(`.mb[data-mode="${m}"]`)?.classList.add('sel');
    const lb = $('#amode-lb'); if (lb) lb.textContent = { rag: 'RAG', agentic: 'Agent', graph: 'Graph', multimodal: 'Multi' }[m] || 'RAG';
  }

  function switchTab(name, e) {
    $$('.ra-tab').forEach(t => t.classList.remove('active'));
    if (e && e.target) e.target.classList.add('active');
    ['dashboard', 'status', 'docs', 'settings', 'sources', 'playground'].forEach(n => { const el = $('#tab-' + n); if (el) el.style.display = n === name ? 'block' : 'none'; });
    if (name === 'dashboard') { chkD(); }
    else if (name === 'status') { chkH(); chkP(); chkG(); }
  }

  async function chkD() {
    try {
      const [health, prewarm, docs, graph] = await Promise.all([
        fetch('/api/health').then(r => r.json()),
        fetch('/api/prewarm/status').then(r => r.json()).catch(() => ({})),
        fetch('/api/documents').then(r => r.json()).catch(() => ({ documents: [] })),
        fetch('/api/graph?node_limit=0').then(r => r.json()).catch(() => ({ stats: {} })),
      ]);
      const svc = health.services || {}; const models = health.models || {};
      let healthHTML = '';
      for (const [k, v] of Object.entries(svc)) {
        const cls = v === 'ok' ? 'ok' : (v === 'unavailable' ? 'err' : 'warn');
        const modelInfo = models[k] ? ` (${typeof models[k]==='string'?models[k]:'available'})` : '';
        healthHTML += `<div class="dash-card ${cls}"><div class="dc-title">${k}</div><div class="dc-val">${v}</div><div class="dc-sub">${modelInfo}</div></div>`;
      }
      $('#dash-health').innerHTML = healthHTML;

      const docCount = (docs.documents || []).length;
      const chunkCount = docCount > 0 ? (docCount * 12) : 0; // Approximate
      $('#dash-index').innerHTML = `<b>${docCount}</b> indexed documents · ~${chunkCount} chunks · <b>${(docs.documents||[]).filter(d=>d.path&&d.path.match(/\.(png|jpg|jpeg|gif)$/i)).length||0}</b> images`;

      const gs = graph.stats || {};
      const kgHTML = `<b>${gs.nodes||0}</b> nodes · <b>${gs.edges||0}</b> edges · <b>${gs.communities||0}</b> communities · density: ${(gs.density||0).toFixed(4)}`;
      $('#dash-kg').innerHTML = kgHTML;

      const pwCount = prewarm.cached_qa_pairs || 0;
      const pwTarget = prewarm.target_count || 150;
      const pwPct = Math.min(100, Math.round(pwCount / pwTarget * 100));
      $('#dash-prewarm').innerHTML = `<b>${pwCount}</b> / ${pwTarget} QA pairs cached<div class="bar-wrap"><div class="bar-fill" style="width:${pwPct}%"></div></div>`;
    } catch (e) {
      $('#dash-health').innerHTML = '<div class="dash-card err"><div class="dc-title">Error</div><div class="dc-val">offline</div></div>';
    }
  }

  async function chkH() { try { const r = await fetch('/api/health'); const d = await r.json(); const svc = d.services || {}; const dots = []; for (const [k, v] of Object.entries(svc)) { const cls = v === 'ok' ? 'g' : (v === 'unavailable' ? 'r' : 'y'); dots.push(`<span class="sd"><span class="d ${cls}"></span>${esc(k)}</span>`); } $('#stat-bar').innerHTML = dots.join('') || '...'; } catch (e) { $('#stat-bar').innerHTML = '<span class="sd"><span class="d r"></span>offline</span>'; } }
  async function chkP() { try { const r = await fetch('/api/prewarm/status'); const d = await r.json(); $('#prewarm-stat').innerHTML = `<p style="font-size:10px;color:var(--td)">${d.cached_qa_pairs || 0}/${d.target_count || 150} QA pairs</p>`; return d; } catch (e) { console.debug('Prewarm status check failed', e); } }
  async function chkG() { try { const r = await fetch('/api/github/status'); const d = await r.json(); if (!d.configured) { $('#gh-stat').innerHTML = '<p style="font-size:10px;color:var(--td)">not configured</p>'; return; } const s = d.cloned ? `cloned (${d.document_count || 0} docs)` : 'not cloned'; $('#gh-stat').innerHTML = `<p style="font-size:10px;color:var(--td)">${s}</p>`; return d; } catch (e) { console.debug('GitHub status check failed', e); $('#gh-stat').innerHTML = '<p style="font-size:10px;color:var(--td)">error</p>'; } }
  async function ghSync() { try { const r = await fetch('/api/github/sync', { method: 'POST' }); const d = await r.json(); $('#gh-stat').innerHTML = `<p style="font-size:10px;color:var(--cream)">${d.message || 'synced'}</p>`; ldD(); } catch (e) { $('#gh-stat').innerHTML = '<p style="font-size:10px;color:#d55">failed</p>'; } }
  async function runEval() { try { await fetch('/api/eval?limit=10', { method: 'POST' }); alert('Eval started.'); } catch (e) { } }
  function updC(n) { const el = $('#doc-count-label'); if (el) el.textContent = n + ' docs'; }

  async function ldD() {
    try { const r = await fetch('/api/documents'); const d = await r.json(); const docs = d.documents || []; updC(docs.length); if (!docs.length) { $('#dlist').innerHTML = '<p style="font-size:10px;color:var(--td)">no documents</p>'; return; } $('#dlist').innerHTML = docs.map(d => { const n = d.path.split(/[/\\]/).pop(); return `<div class="doc-row"><span>${esc(n)}</span><span class="del" onclick="App.delDoc('${esc(d.hash || '').replace(/'/g, "\\'")}')" title="删除此文档">x</span></div>`; }).join(''); } catch (e) { }
  }

  async function delDoc(h) { await fetch('/api/documents/' + h, { method: 'DELETE' }); ldD(); }

  const upz = $('#upz'), fip = $('#fip');
  if (upz && fip) { upz.addEventListener('click', () => fip.click()); upz.addEventListener('dragover', e => e.preventDefault()); upz.addEventListener('drop', e => { e.preventDefault(); if (e.dataTransfer.files.length) upld(e.dataTransfer.files); }); fip.addEventListener('change', () => { if (fip.files.length) upld(fip.files); }); }

  async function upld(files) { const fd = new FormData(); for (const f of files) fd.append('files', f); const r = await fetch('/api/upload', { method: 'POST', body: fd }); const d = await r.json(); if (d.file_paths?.length) { const ir = await fetch('/api/index', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ file_paths: d.file_paths, incremental: !0 }) }); const id = await ir.json(); poll(id.task_id); } }
  async function poll(tid) { for (let i = 0; i < 60; i++) { await new Promise(r => setTimeout(r, 2000)); const r = await fetch(`/api/task/${tid}`); const d = await r.json(); if (d.state === 'SUCCESS') { ldD(); return; } if (d.state === 'FAILURE') return; } }

  function enter() { lenis.stop(); const ov = $('#rag-app'); ov.classList.add('open'); gsap.fromTo(ov, { opacity: 0 }, { opacity: 1, duration: .6, ease: 'power3.out' }); ldD(); chkH(); chkP(); chkG(); }
  function leave() { gsap.to('#rag-app', { opacity: 0, duration: .5, ease: 'power2.in', onComplete: () => { const ov = $('#rag-app'); ov.classList.remove('open'); ov.style.opacity = ''; lenis.start(); } }); }

  document.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey && document.activeElement === $('#qinput')) { e.preventDefault(); send(); } if (e.key === 'Escape' && streaming) { stopStream(); } });

  (function () {
    const qs = ['减震结构设计要点', '驱动轮与地面的作用力公式', '弹簧预压力的作用', 'Flex调试准备'];
    const el = $('#quick-row'); if (el) el.innerHTML = qs.map(q => `<button class="quick-q">${esc(q)}</button>`).join('');
    $$('.quick-q').forEach(b => b.addEventListener('click', () => { $('#qinput').value = b.textContent; send(); }));
  })();

  (async function loadStats() {
    try {
      const [pr, dr] = await Promise.all([fetch('/api/prewarm/status').then(r => r.json()), fetch('/api/documents').then(r => r.json())]);
      const st1 = document.querySelector('#st1 .stat-num'); if (st1) { st1.dataset.countup = pr.cached_qa_pairs || 147; st1.textContent = '0'; }
      const docs = dr.documents || []; const st2 = document.querySelector('#st2 .stat-num'); if (st2) { st2.dataset.countup = docs.length || 45; st2.textContent = '0'; }
    } catch (e) { }
  })();

  let _graphData = null, _graphNet = null;
  async function showGraph() { const ov = $('#graph-overlay'); ov.style.display = 'block'; try { const r = await fetch('/api/graph?node_limit=200'); _graphData = await r.json(); const s = _graphData.stats || {}; $('#graph-stats').textContent = `${s.displayed_nodes || 0}/${s.node_count || 0} nodes, ${s.displayed_edges || 0}/${s.edge_count || 0} edges`; const nodes = new vis.DataSet(_graphData.nodes.map(n => ({ id: n.id, label: n.label, value: n.degree, title: `${n.label}\ndegree: ${n.degree}\nchunks: ${(n.chunks || []).length}` }))); const edges = new vis.DataSet(_graphData.edges.map(e => ({ from: e.from, to: e.to, label: e.label, arrows: 'to' }))); const data = { nodes, edges }; const opts = { physics: { solver: 'forceAtlas2Based', forceAtlas2Based: { gravitationalConstant: -50, centralGravity: 0.01, springLength: 150, springConstant: 0.08 } }, edges: { smooth: { type: 'continuous' }, font: { size: 9, color: 'var(--td)' } }, nodes: { font: { size: 12, color: 'var(--cream)' }, color: { background: 'var(--gold)', border: 'var(--cream)' } }, interaction: { hover: true, tooltipDelay: 200 } }; _graphNet = new vis.Network($('#graph-container'), data, opts); _graphNet.on('doubleClick', e => { if (e.nodes.length) { const n = e.nodes[0]; const nd = _graphData.nodes.find(x => x.id === n); if (nd && nd.chunks && nd.chunks.length) { $('#qinput').value = '关于"' + nd.label + '"的详细信息'; $('#rag-app').classList.add('open'); send(); } } }); } catch (e) { $('#graph-stats').textContent = '加载失败'; } }

  function closeGraph() { const ov = $('#graph-overlay'); ov.style.display = 'none'; if (_graphNet) { _graphNet.destroy(); _graphNet = null; } _graphData = null; }

  function filterGraph() { const q = ($('#graph-search').value || '').toLowerCase(); if (!_graphNet || !_graphData) return; if (!q) { _graphNet.selectNodes([]); return; } const ids = _graphData.nodes.filter(n => n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q)).map(n => n.id); _graphNet.selectNodes(ids); if (ids.length === 1) _graphNet.focus(ids[0], { scale: 2, animation: true }); }

  async function runPlayground() {
    const q = $('#qinput').value || 'Flex调试';
    const body = JSON.stringify({ question: q, top_k: +($('#pg-topk').value || 5), alpha: +($('#pg-alpha').value || 0.5) });
    const el = $('#pg-result'); el.innerHTML = '<span style="color:var(--gold)">running...</span>';
    try {
      const r = await fetch('/api/playground/query', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
      const d = await r.json(); const t = d.trace || {};
      const steps = (t.steps || []).map(s => {
        let detail = '';
        if (s.step === 'intent') detail = s.result;
        else if (s.step === 'retrieval') detail = `${s.candidate_count} candidates`;
        else if (s.step === 'rerank') detail = (s.top_scores || []).map(x => `${x[1]} ${x[0].slice(0, 30)}`).join('<br>') || 'none';
        else if (s.step === 'generation') detail = `${s.model}, ${s.context_chunks} ctx, ${s.citation_count} cites`;
        return `<div style="margin:6px 0;padding:6px;border-left:2px solid var(--gold);font-size:10px"><b>${s.step}</b> <span style="color:var(--td)">${(t.timing_ms || {})[s.step] || '?'}ms</span><br><span style="color:var(--td)">${detail}</span></div>`;
      }).join('');
      el.innerHTML = steps + `<div style="margin-top:8px;font-size:11px"><b>Total:</b> ${t.timing_ms?.total || '?'}ms</div><div style="margin-top:8px;padding:8px;background:var(--gh);border-radius:6px;font-size:11px;max-height:200px;overflow-y:auto"><b>Answer:</b><br>${renderMD((d.answer || '').slice(0, 500))}</div>`;
    } catch (e) { el.innerHTML = '<span style="color:#d55">' + e.message + '</span>'; }
  }

  function regenerate() {
    if (!_lastQuestion) return;
    $('#qinput').value = _lastQuestion;
    send();
  }

  function toggleDarkMode() {
    const root = document.documentElement;
    const isDark = root.style.getPropertyValue('--ink') !== '#fafafa';
    if (isDark) {
      root.style.setProperty('--ink', '#fafafa');
      root.style.setProperty('--cream', '#1a1a2e');
      root.style.setProperty('--gold', '#8b6914');
      root.style.setProperty('--td', 'rgba(26,26,46,.5)');
      root.style.setProperty('--gh', 'rgba(139,105,20,.08)');
      root.style.setProperty('--gm', 'rgba(139,105,20,.15)');
      root.style.setProperty('--ash', 'rgba(245,245,250,.8)');
      root.style.setProperty('--rise', 'rgba(235,235,245,.9)');
      root.style.setProperty('--void', 'rgba(250,250,250,.9)');
      root.style.setProperty('--tm', 'rgba(26,26,46,.28)');
      root.style.setProperty('--gd', 'rgba(139,105,20,.3)');
    } else {
      root.style.setProperty('--ink', '#06060C');
      root.style.setProperty('--cream', '#F5F0E8');
      root.style.setProperty('--gold', '#D4C098');
      root.style.setProperty('--td', 'rgba(245,240,232,.5)');
      root.style.setProperty('--gh', 'rgba(212,192,152,.06)');
      root.style.setProperty('--gm', 'rgba(212,192,152,.15)');
      root.style.setProperty('--ash', 'rgba(14,14,26,.8)');
      root.style.setProperty('--rise', 'rgba(24,24,48,.9)');
      root.style.setProperty('--void', 'rgba(6,6,12,.9)');
      root.style.setProperty('--tm', 'rgba(245,240,232,.28)');
      root.style.setProperty('--gd', 'rgba(212,192,152,.4)');
    }
  }

  function clearSearchHistory() { clearHistory(); renderHistory(); }

  // ── Initialize dark mode toggle ──
  (function initDarkModeToggle() {
    const btn = document.createElement('button');
    btn.className = 'dm-toggle'; btn.title = 'Toggle theme'; btn.textContent = '🌓';
    btn.addEventListener('click', toggleDarkMode);
    document.body.appendChild(btn);
  })();

  // ── Initialize search history ──
  renderHistory();

  return { enter, leave, setMode, send, switchTab, copyMsg, fb, showCite, showChunk, showGraph, closeGraph, filterGraph, ghSync, runEval, delDoc, runPlayground, regenerate, toggleDarkMode, clearSearchHistory };
})();
