
document.addEventListener('DOMContentLoaded', () => {
  // Automatically activate on any input with data-live-search-url attribute
  const searchInputs = document.querySelectorAll('[data-live-search-url]');

  searchInputs.forEach(searchInput => {
    const url = searchInput.dataset.liveSearchUrl;
    const targetSelector = searchInput.dataset.liveSearchTarget || 'table tbody';
    const tableBody = document.querySelector(targetSelector);

    let debounceTimer = null;
    let controller = null;

    searchInput.addEventListener('keyup', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        const query = this.value.trim();

        // Cancel old request if user types fast
        if (controller) controller.abort();
        controller = new AbortController();
        const signal = controller.signal;

        const fullUrl = url + '?q=' + encodeURIComponent(query);

        fetch(fullUrl, { signal })
          .then(response => {
            if (!response.ok) throw new Error('HTTP ' + response.status);
            return response.text();
          })
          .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newTbody = doc.querySelector(targetSelector);
            if (newTbody && tableBody) {
              tableBody.innerHTML = newTbody.innerHTML;
            } else {
              console.warn('Could not find target element:', targetSelector);
            }
          })
          .catch(err => {
            if (err.name === 'AbortError') return; // ignore aborted requests
            console.error('Live search error:', err);
          });
      }, 400);
    });
  });
});
