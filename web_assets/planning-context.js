/* Local return context only. No storage, tracking, or inferred trip state. */
(() => {
  function localPath(value) {
    if (!value || value.length > 6000 || !value.startsWith('/') || value.startsWith('//')) return null;
    try {
      const url = new URL(value, location.origin);
      if (url.origin !== location.origin || !/^\/(search|camping|knowledge|evidence|parks|trails|peaks)\//.test(url.pathname)) return null;
      return url.pathname + url.search + url.hash;
    } catch (_) { return null; }
  }
  const from = localPath(new URLSearchParams(location.search).get('from'));
  if (from) {
    let back = document.querySelector('[data-context-back]');
    if (!back) {
      back = document.createElement('a');
      back.dataset.contextBack = '';
      (document.querySelector('main') || document.querySelector('.page-header') || document.body).prepend(back);
    }
    back.href = from;
    back.textContent = from.startsWith('/search/') ? '← Back to search results' :
      from.includes('/campsites/') ? '← Back to campsite list' :
      from.startsWith('/camping/') ? '← Back to camping' : '← Back to ' + (new URLSearchParams(location.search).get('from_label') || 'previous page').slice(0,120);
    const parentLink = document.querySelector('[data-parent-link]');
    back.hidden = Boolean(parentLink && new URL(parentLink.href).pathname === new URL(from,location.origin).pathname);
  }
  document.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link || link.hasAttribute('data-context-back') || link.target || link.hasAttribute('download')) return;
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || !/^\/(knowledge|evidence)\//.test(url.pathname)) return;
    if (url.pathname === location.pathname) return;
    const selected = link.closest('.camp-row');
    if (selected?.id) history.replaceState(null, '', location.pathname + location.search + '#' + encodeURIComponent(selected.id));
    const current = location.pathname + location.search + location.hash;
    if (current.length > 5000) return;
    url.searchParams.set('from', current);
    const title = document.querySelector('h1')?.textContent.trim();
    if (title) url.searchParams.set('from_label',title.slice(0,120));
    link.href = url.pathname + url.search + url.hash;
  });
})();
