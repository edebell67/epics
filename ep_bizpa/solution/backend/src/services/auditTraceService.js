const sortTimelineEntries = (entries) => entries
  .slice()
  .sort((left, right) => {
    const leftTime = new Date(left.timestamp || left.created_at || 0).getTime();
    const rightTime = new Date(right.timestamp || right.created_at || 0).getTime();
    if (leftTime !== rightTime) return leftTime - rightTime;
    return String(left.event_id || left.snapshot_id || '').localeCompare(String(right.event_id || right.snapshot_id || ''));
  });

const reconstructAuditTrace = ({ events = [], snapshots = [] }) => {
  const duplicateEventIds = [];
  const seenEventIds = new Set();
  const timeline = [];
  const uniqueEntities = new Set();
  const eventTypes = new Set();
  const quarterReferences = new Set();

  for (const event of sortTimelineEntries(events)) {
    if (seenEventIds.has(event.event_id)) {
      duplicateEventIds.push(event.event_id);
    }
    seenEventIds.add(event.event_id);
    if (event.entity_id) uniqueEntities.add(String(event.entity_id));
    if (event.quarter_reference) quarterReferences.add(String(event.quarter_reference));
    if (event.event_type) eventTypes.add(String(event.event_type));
    timeline.push({
      kind: 'event',
      event_id: event.event_id,
      event_type: event.event_type,
      entity_id: event.entity_id || null,
      entity_type: event.entity_type || null,
      timestamp: event.timestamp || event.created_at,
      description: event.description || null,
      quarter_reference: event.quarter_reference || null,
      status_from: event.status_from || null,
      status_to: event.status_to || null
    });
  }

  for (const snapshot of sortTimelineEntries(snapshots)) {
    if (snapshot.snapshot_id) uniqueEntities.add(String(snapshot.snapshot_id));
    if (snapshot.quarter_reference) quarterReferences.add(String(snapshot.quarter_reference));
    timeline.push({
      kind: 'snapshot',
      snapshot_id: snapshot.snapshot_id,
      timestamp: snapshot.timestamp || snapshot.created_at,
      quarter_reference: snapshot.quarter_reference || null,
      description: snapshot.description || null,
      included_transaction_ids: snapshot.included_transaction_ids || []
    });
  }

  const sortedTimeline = sortTimelineEntries(timeline);
  return {
    immutable_history: duplicateEventIds.length === 0,
    duplicate_event_ids: duplicateEventIds,
    total_events: events.length,
    snapshot_count: snapshots.length,
    unique_entities: Array.from(uniqueEntities).sort(),
    event_types: Array.from(eventTypes).sort(),
    quarter_references: Array.from(quarterReferences).sort(),
    timeline: sortedTimeline
  };
};

module.exports = {
  reconstructAuditTrace
};
