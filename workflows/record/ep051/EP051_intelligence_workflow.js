/* VERSION HISTORY
 * v1.0.1 · 2026-08-24 · Readable, syntax-verified hierarchy renderer.
 * v1.0.0 · 2026-08-24 · Shared hierarchy renderer, filters and side inspector.
 */
(function () {
  const progressClass = pct => pct === 100 ? 'complete' : pct === 0 ? 'blocked' : 'partial';
  function init() {
    const lanes = globalThis.WORKFLOW_LANES || [];
    const nodes = globalThis.WORKFLOW_NODES || [];
    const map = document.querySelector('#map');
    const side = document.querySelector('#side');
    document.querySelector('#nodeCount').textContent = nodes.length;
    document.querySelector('#coverage').textContent = Math.round(nodes.reduce((sum, node) => sum + node.pct, 0) / Math.max(1, nodes.length)) + '%';

    function render(filter = 'all') {
      map.innerHTML = '';
      lanes.forEach(lane => {
        const visible = nodes.filter(node => node.lane === lane.id && (filter === 'all' || filter === lane.id));
        if (!visible.length) return;
        const section = document.createElement('section');
        section.className = 'lane';
        section.innerHTML = `<h2>${lane.title}</h2><p class="who">${lane.description}</p><div class="flow">${visible.map(node => `<button class="node" data-id="${node.id}"><span class="tag">${node.id}</span><h3>${node.title}</h3><p>${node.purpose}</p><code class="stage">${node.executor}</code><span class="progress ${progressClass(node.pct)}">${node.pct}% · ${node.status}</span>${node.child ? `<a class="child" href="${node.child}">Open child workflow →</a>` : ''}</button>`).join('')}</div>`;
        map.append(section);
      });
      map.querySelectorAll('.node').forEach(button => button.addEventListener('click', event => {
        if (!event.target.closest('a')) select(button.dataset.id);
      }));
    }

    function select(id) {
      document.querySelectorAll('.node').forEach(node => node.classList.toggle('sel', node.dataset.id === id));
      const node = nodes.find(candidate => candidate.id === id);
      side.innerHTML = `<h2>${node.title}</h2><p class="sub">${node.id} · ${node.pct}% · ${node.status}</p><p>${node.purpose}</p><h4>Automated steps</h4><ol>${node.steps.map(step => `<li>${step}</li>`).join('')}</ol><h4>Completion test</h4><p class="box test">${node.test}</p><h4>Evidence</h4><p class="box ev">${node.evidence}</p><h4>Dependencies</h4><p class="box dep">${node.dependencies}</p><h4>Automation correspondence</h4><p class="box auto">${node.executor}</p>${node.child ? `<a class="child" href="${node.child}">Open dedicated child process →</a>` : ''}`;
    }

    document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => {
      document.querySelectorAll('[data-filter]').forEach(candidate => candidate.classList.toggle('on', candidate === button));
      render(button.dataset.filter);
    }));
    render();
    if (nodes[0]) select(nodes[0].id);
  }
  document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', init) : init();
})();
