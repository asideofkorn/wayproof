/* Static pagination is the fallback; load compact child summaries on filtering. */
(() => {
  const form = document.getElementById('camp-filter');
  if (!form) return;
  const input = document.getElementById('camp-query');
  const results = document.getElementById('camp-results');
  const count = document.getElementById('camp-count');
  const pages = document.getElementById('camp-pages');
  const initialHTML = results.innerHTML, initialCount = count.textContent;
  let rows, pending, sequence = 0;
  function restoreSelection() {
    let id; try { id = decodeURIComponent(location.hash.slice(1)); } catch (_) { return; }
    const selected = document.getElementById(id);
    if (selected && results.contains(selected)) {
      selected.scrollIntoView({block:'center'});
      selected.querySelector('a')?.focus({preventScroll:true});
    }
  }
  async function filter(save = true) {
    const request = ++sequence;
    const query = input.value.trim();
    if (save) {
      const url = new URL(location.href);
      query ? url.searchParams.set('q', query) : url.searchParams.delete('q');
      history.replaceState(null, '', url.pathname + url.search);
    }
    if (!query) {
      results.innerHTML = initialHTML; count.textContent = initialCount; pages.hidden = false; document.getElementById('camp-filter-pages')?.remove(); if (!save) restoreSelection(); return;
    }
    try {
      if (!rows) {
        pending ||= fetch(form.dataset.index).then(r => { if (!r.ok) throw Error(); return r.json(); });
        rows = await pending;
      }
      if (request !== sequence) return;
      const terms = query.toLocaleLowerCase().split(/\s+/);
      const matches = rows.filter(r => terms.every(t => (r.name + ' ' + r.detail).toLocaleLowerCase().includes(t)));
      results.replaceChildren();
      // Bound each filtered result page; next/previous buttons stay local.
      let page = Number(new URLSearchParams(location.search).get('p') || 1);
      page = Math.min(Math.max(1, page || 1), Math.max(1, Math.ceil(matches.length / 20)));
      for (const row of matches.slice((page-1)*20,page*20)) {
        const li = document.createElement('li'); li.className = 'camp-row'; li.id = row.id;
        const h = document.createElement('h2'), a = document.createElement('a');
        a.href = row.url; a.textContent = row.name; h.append(a);
        const p = document.createElement('p'); p.textContent = row.detail; li.append(h,p);
        const ul = document.createElement('ul');
        row.warnings.forEach(w => { const note = document.createElement('li'); note.textContent = w; ul.append(note); });
        li.append(ul); results.append(li);
      }
      count.textContent = `${matches.length} matching ${matches.length === 1 ? 'campsite' : 'campsites'} · Page ${page} of ${Math.max(1,Math.ceil(matches.length/20))}`;
      pages.hidden = true;
      document.getElementById('camp-filter-pages')?.remove();
      const nav = document.createElement('nav'); nav.id = 'camp-filter-pages'; nav.setAttribute('aria-label','Filtered campsite pages');
      for (const [label,p] of [['Previous',page-1],['Next',page+1]]) {
        if (p < 1 || p > Math.ceil(matches.length/20)) continue;
        const button = document.createElement('button'); button.type = 'button'; button.textContent = label;
        button.addEventListener('click', () => { const url = new URL(location.href);url.searchParams.set('p',p);history.replaceState(null,'',url.pathname+url.search);filter(false); });
        nav.append(button);
      }
      results.after(nav);
      if (!save) restoreSelection();
    } catch (_) {
      pending = null;
      count.textContent = 'Filtering could not load. Use the page links below to browse campsites.';
      results.innerHTML = initialHTML; pages.hidden = false;
    }
  }
  form.addEventListener('submit', e => { e.preventDefault(); filter(); });
  input.addEventListener('input', () => { const u = new URL(location.href);u.searchParams.delete('p');history.replaceState(null,'',u.pathname+u.search);filter(); });
  function restore() { input.value = new URLSearchParams(location.search).get('q') || ''; filter(false); }
  window.addEventListener('pageshow', restore); window.addEventListener('popstate',restore); restore();
})();
