// VERSION HISTORY v1.0.0 · 2026-09-02 · Keep checklist status in sync with authoritative node evidence.
const rows = document.querySelector('tbody');
rows.replaceChildren();
for (const node of window.EP052_WORKFLOW.nodes) {
  const row = document.createElement('tr'), name = document.createElement('td');
  const link = document.createElement('a');
  link.href = 'workflows/EP052_'+node.lane.toLowerCase()+'_workflow.html#'+node.id;
  link.textContent = node.id+' · '+node.title; name.append(link); row.append(name);
  const status=document.createElement('td');status.textContent=node.pct+'% · '+node.status;row.append(status);
  const evidence=document.createElement('td');evidence.textContent=node.test+' Evidence: '+node.evidence;
  if(node.deliverable){const a=document.createElement('a');a.href=node.deliverable;a.textContent=' Open deliverable';evidence.append(a);}
  row.append(evidence);rows.append(row);
}
