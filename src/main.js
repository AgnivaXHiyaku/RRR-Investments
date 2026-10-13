import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { createStage } from './scene.js';
import { TEAM, POSTS, API } from './content.js';

gsap.registerPlugin(ScrollTrigger);
document.documentElement.classList.add('js');
const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
document.getElementById('year').textContent = new Date().getFullYear();

// ---------- smooth scroll ----------
const lenis = new Lenis({ duration: 1.15, smoothWheel: !reduced });
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add((time) => lenis.raf(time * 1000));
gsap.ticker.lagSmoothing(0);

document.querySelectorAll('a[href^="#"]').forEach((a) => {
  a.addEventListener('click', (e) => {
    const id = a.getAttribute('href');
    const el = id.length > 1 && document.querySelector(id);
    if (!el) return;
    e.preventDefault();
    closeMenu();
    lenis.scrollTo(el, { offset: id === '#top' ? 0 : -40 });
  });
});

// ---------- nav ----------
const nav = document.getElementById('nav');
ScrollTrigger.create({ start: 80, onToggle: (s) => nav.classList.toggle('is-scrolled', s.isActive) });
const burger = document.getElementById('burger');
const mnav = document.getElementById('mnav');
function closeMenu() { mnav.classList.remove('is-open'); burger.setAttribute('aria-expanded', 'false'); lenis.start(); }
burger.addEventListener('click', () => {
  const open = !mnav.classList.contains('is-open');
  mnav.classList.toggle('is-open', open);
  burger.setAttribute('aria-expanded', String(open));
  open ? lenis.stop() : lenis.start();
});

// ---------- dynamic content ----------
const esc = (s = '') => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const titleCase = (s) => s.toLowerCase().replace(/\b([a-z])/g, (m) => m.toUpperCase()).replace(/\bCma\b/, 'CMA');

function renderTeam(list) {
  document.getElementById('teamGrid').innerHTML = list.map((m) => {
    const li = (m.socialMedia || []).find((s) => s.platform === 'linkedin');
    return `<article class="member reveal">
      <div class="member__img"><img src="${esc(m.image)}" alt="${esc(titleCase(m.name))}" loading="lazy" /></div>
      <div class="member__body">
        <h3 class="member__name">${esc(titleCase(m.name))}</h3>
        <p class="member__role">${esc(m.designation)}</p>
        ${m.sectorsCovered?.length ? `<p class="member__sectors">Covers ${esc(m.sectorsCovered.join(' · '))}</p>` : ''}
        ${li ? `<a class="member__in" href="${esc(li.url)}" target="_blank" rel="noopener">LinkedIn ↗</a>` : ''}
      </div>
    </article>`;
  }).join('');
}

function renderPosts(list) {
  // the same story is often cross-posted; show one card per title
  const seen = new Set();
  const uniq = list.filter((p) => !seen.has(p.title) && seen.add(p.title));
  const cards = uniq.map((p) => `<a class="post reveal" href="${esc(p.link)}" target="_blank" rel="noopener">
      <div class="post__img"><img src="${esc(p.image)}" alt="" loading="lazy" /></div>
      <div class="post__body">
        <span class="post__sub">${esc(p.subTitle || 'Insight')}</span>
        <h3 class="post__title">${esc(p.title)}</h3>
        <p class="post__desc">${esc(p.description)}</p>
        <span class="post__more">Explore the complete story ↗</span>
      </div>
    </a>`);
  cards.push(`<div class="post post--ghost reveal"><p>More research and market outlooks are on the way.</p><a class="link" href="https://x.com/RRRinvestments" target="_blank" rel="noopener">Follow @RRRinvestments</a></div>`);
  document.getElementById('insightsGrid').innerHTML = cards.join('');
}

renderTeam(TEAM);
renderPosts(POSTS);

// refresh from the live CMS when it's reachable; keep the static copy otherwise
const fetchJSON = (url) => fetch(url, { headers: { 'Content-Type': 'application/json' } }).then((r) => (r.ok ? r.json() : Promise.reject(r)));
Promise.allSettled([fetchJSON(`${API}/website/teams`), fetchJSON(`${API}/website/posts`)]).then(([t, p]) => {
  let changed = false;
  if (t.status === 'fulfilled' && t.value?.data?.length) { renderTeam([...t.value.data].sort((a, b) => a.order - b.order)); changed = true; }
  if (p.status === 'fulfilled' && p.value?.data?.posts?.length) { renderPosts(p.value.data.posts); changed = true; }
  if (changed) { bindReveals(); ScrollTrigger.refresh(); }
});

// ---------- split headings into words ----------
function splitWords(el) {
  const walk = (node) => {
    [...node.childNodes].forEach((n) => {
      if (n.nodeType === 3) {
        const frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach((part) => {
          if (!part) return;
          if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
          const w = document.createElement('span'); w.className = 'w';
          const i = document.createElement('span'); i.textContent = part;
          w.appendChild(i); frag.appendChild(w);
        });
        n.replaceWith(frag);
      } else if (n.nodeType === 1) walk(n);
    });
  };
  walk(el);
}
document.querySelectorAll('.split, .split-words').forEach(splitWords);

// ---------- reveals ----------
function bindReveals() {
  document.querySelectorAll('.reveal:not([data-bound])').forEach((el) => {
    el.dataset.bound = '1';
    if (reduced) return;
    gsap.to(el, {
      opacity: 1, y: 0, duration: 1.1, ease: 'expo.out',
      scrollTrigger: { trigger: el, start: 'top 88%', once: true },
    });
  });
}
bindReveals();

if (!reduced) {
  document.querySelectorAll('.split').forEach((el) => {
    gsap.from(el.querySelectorAll('.w > span'), {
      yPercent: 110, duration: 1.2, ease: 'expo.out', stagger: 0.04,
      scrollTrigger: { trigger: el, start: 'top 85%', once: true },
    });
  });
  // interlude: words light up as you scroll through
  const words = document.querySelectorAll('.split-words .w > span');
  gsap.fromTo(words, { opacity: 0.12 }, {
    opacity: 1, stagger: 0.1, ease: 'none',
    scrollTrigger: { trigger: '.interlude', start: 'top 70%', end: 'center 45%', scrub: true },
  });
}

// ---------- counters ----------
document.querySelectorAll('[data-count]').forEach((el) => {
  const to = +el.dataset.count;
  ScrollTrigger.create({
    trigger: el, start: 'top 85%', once: true,
    onEnter: () => gsap.to({ v: 0 }, { v: to, duration: 1.6, ease: 'power3.out', onUpdate() { el.textContent = Math.round(this.targets()[0].v); } }),
  });
});

// ---------- the 3D stage ----------
const bar = document.getElementById('loaderBar');
const loaderEl = document.getElementById('loader');
let revealed = false;
function revealPage(stage) {
  if (revealed) return;
  revealed = true;
  bar.style.width = '100%';
  setTimeout(() => {
    loaderEl.classList.add('is-done');
    stage?.startIntro();
    if (!reduced) {
      gsap.from('.hero__title .line > *', { yPercent: 115, duration: 1.5, ease: 'expo.out', stagger: 0.08, delay: 0.15 });
      gsap.from('.hero__glyph', { opacity: 0, y: 20, duration: 1.6, delay: 0.8, ease: 'expo.out' });
    }
  }, 350);
}

let stage = null;
try {
  stage = createStage(document.getElementById('stage'), {
    onProgress: (p) => { bar.style.width = `${Math.round(p * 100)}%`; },
    onReady: () => revealPage(stage),
  });
} catch (err) {
  console.warn('[stage] WebGL unavailable, continuing without 3D', err);
  document.getElementById('stage').style.display = 'none';
}
// never hold the page hostage to a slow model
setTimeout(() => revealPage(stage), 6000);
if (!stage) revealPage(null);

if (stage) {
  document.querySelectorAll('[data-scene]').forEach((el) => {
    ScrollTrigger.create({
      trigger: el,
      start: 'top 55%',
      end: 'bottom 55%',
      onToggle: (s) => { if (s.isActive) stage.setState(el.dataset.scene); },
      onUpdate: (s) => { if (s.isActive) stage.setProgress(s.progress); },
    });
  });
  const nodeCount = document.getElementById('nodeCount');
  gsap.ticker.add(() => {
    if (nodeCount && stage.nodeTotal) nodeCount.textContent = String(stage.nodeLit).padStart(2, '0');
  });
}

// ---------- chapter rail ----------
const railLinks = document.querySelectorAll('.rail a');
document.querySelectorAll('[data-chapter]').forEach((el) => {
  ScrollTrigger.create({
    trigger: el, start: 'top 50%', end: 'bottom 50%',
    onToggle: (s) => {
      if (!s.isActive) return;
      railLinks.forEach((l) => l.classList.toggle('is-active', l.dataset.rail === el.dataset.chapter));
    },
  });
});

// ---------- contact form ----------
const form = document.getElementById('contactForm');
const err = document.getElementById('formErr');
const btn = document.getElementById('formBtn');
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  err.textContent = '';
  const data = Object.fromEntries(new FormData(form).entries());
  const labels = { fullName: 'Full name', email: 'Email', phoneNumber: 'Phone number', yourQuery: 'Your query' };
  for (const [k, label] of Object.entries(labels)) {
    const field = form.elements[k];
    field.removeAttribute('aria-invalid');
    if (!String(data[k] || '').trim()) {
      field.setAttribute('aria-invalid', 'true'); field.focus();
      err.textContent = `"${label}" is required.`;
      return;
    }
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
    form.elements.email.setAttribute('aria-invalid', 'true'); form.elements.email.focus();
    err.textContent = 'Please enter a valid email address.';
    return;
  }
  btn.disabled = true;
  btn.firstChild.textContent = 'Sending… ';
  try {
    const res = await fetch(`${API}/website/contacts/inquiries/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ responses: data }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.message || 'Something went wrong.');
    }
    form.classList.add('is-sent');
    document.getElementById('formOk').hidden = false;
  } catch (ex) {
    err.innerHTML = `${esc(ex.message || 'Something went wrong.')} You can also write to us at <a href="mailto:info@rrrinvestments.com">info@rrrinvestments.com</a>.`;
  } finally {
    btn.disabled = false;
    btn.firstChild.textContent = 'Schedule a Discovery Call ';
  }
});

window.addEventListener('load', () => ScrollTrigger.refresh());
