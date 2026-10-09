(() => {
  const query = document.getElementById('entity-search');
  const kind = document.getElementById('entity-kind');
  const form = document.getElementById('entity-search-form');
  const count = document.getElementById('result-count');
  const empty = document.getElementById('no-results');
  const results = document.getElementById('entity-results');
  const pages = document.getElementById('search-pages');
  let rows, pending, sequence = 0;
  async function filterEntities(save = true) {
    const request = ++sequence;
    const needle = query.value.trim();
    if (save) {
      const params = new URLSearchParams();
      if (needle) params.set('q',needle);
      if (kind.value) params.set('kind',kind.value);
      history.replaceState(null,'', '/search/' + (params.size ? '?' + params : ''));
    }
    if (!needle && !kind.value) {
      results.replaceChildren(); pages.replaceChildren(); empty.hidden = true;
      count.textContent = 'Enter a name or choose a type to search.'; return;
    }
    try {
      if (!rows) {
        pending ||= fetch('/search/lookup.json').then(r => { if (!r.ok) throw Error(); return r.json(); });
        rows = await pending;
      }
      if (request !== sequence) return;
      const matches = rows.filter(row => WayproofSearch.discover(row,needle,kind.value));
      if (/\d/.test(needle)) matches.sort((a,b) => Number(b.parents.length > 0 && WayproofSearch.matches(b.name,needle)) - Number(a.parents.length > 0 && WayproofSearch.matches(a.name,needle)));
      const pageCount = Math.max(1,Math.ceil(matches.length / 20));
      const p = Math.min(pageCount,Math.max(1,Number(new URLSearchParams(location.search).get('p')) || 1));
      results.replaceChildren(); pages.replaceChildren();
      matches.slice((p-1)*20,p*20).forEach(row => {
        const li = document.createElement('li');li.className = 'result-card';
        const a = document.createElement('a');a.href = row.url;
        a.textContent = row.display_name || row.name;
        const label = document.createElement('p');label.className='meta';
        label.textContent = row.parents.length ? row.parents.map(p=>p.name).join(' · ') : row.label;
        const topics = document.createElement('p');topics.textContent = row.topics;
        li.append(a,label,topics);results.append(li);
      });
      count.textContent = `${matches.length} ${matches.length === 1 ? 'result' : 'results'} · Page ${p} of ${pageCount}`;
      empty.hidden = matches.length !== 0;
      for (const [label,next] of [['Previous',p-1],['Next',p+1]]) {
        if (next < 1 || next > pageCount) continue;
        const a = document.createElement('a'); const url = new URL(location.href);url.searchParams.set('p',next);
        a.href = url.pathname + url.search;a.textContent = label;
        a.addEventListener('click',e=>{e.preventDefault();history.replaceState(null,'',a.href);filterEntities(false);count.focus();});pages.append(a);
      }
    } catch (_) { pending=null;count.textContent='Search could not load. Use the browse links below.'; }
  }
  query.addEventListener('input',()=>filterEntities());
  kind.addEventListener('change',()=>filterEntities());
  query.addEventListener('keydown',event=>{if(event.key === 'Enter'){event.preventDefault();form.requestSubmit();}});
  form.addEventListener('submit',event=>{event.preventDefault();filterEntities().then(()=>count.focus());});
  function restore() {
    const params = new URLSearchParams(location.search);
    query.value = params.get('q') || '';
    kind.value = [...kind.options].some(o=>o.value===params.get('kind')) ? params.get('kind') : '';
    filterEntities(false);
  }
  window.addEventListener('pageshow',restore);window.addEventListener('popstate',restore);restore();
})();
