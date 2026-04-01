import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';

const SYNC_QUEUE_KEY = '@bizpa_sync_queue';
const LAST_SYNC_TS_KEY = '@bizpa_last_sync_ts';
const DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000000';
const DEFAULT_DEVICE_ID = 'mobile-app-001';
const SYNC_ROUTE_PREFIX = '/sync';

export type SyncOperationType = 'upsert' | 'delete';
export type SyncStatus = 'pending' | 'syncing' | 'retry_scheduled' | 'conflict' | 'synced' | 'error';

export interface SyncItem {
  sync_item_id: string;
  tenant_id: string;
  table_name: string;
  entity_id: string;
  entity_version: string;
  operation_type: SyncOperationType;
  queued_at: string;
  sync_status: SyncStatus;
  retry_count: number;
  data: Record<string, unknown>;
  last_error?: string | null;
}

type LegacySyncItem = {
  id?: string;
  tenant_id?: string;
  table_name: string;
  entity_id: string;
  action?: SyncOperationType;
  operation_type?: SyncOperationType;
  data: Record<string, unknown>;
  timestamp?: string;
  queued_at?: string;
  entity_version?: string;
  sync_status?: SyncStatus;
  retry_count?: number;
  last_error?: string | null;
};

type SyncContext = {
  deviceId?: string;
  tenantId?: string;
};

type PushResult = {
  sync_item_id: string;
  entity_id: string;
  status: 'success' | 'error' | 'conflict';
  sync_status?: SyncStatus;
  retry_count?: number;
  entity_version?: string;
  error?: string | null;
};

const buildIsoNow = () => new Date().toISOString();

const resolveSyncUrl = (apiBaseUrl: string, route: string) =>
  apiBaseUrl.endsWith('/api/v1')
    ? `${apiBaseUrl}${route}`
    : `${apiBaseUrl}/api/v1${route}`;

const normalizeQueueItem = (item: LegacySyncItem): SyncItem => {
  const queuedAt = item.queued_at || item.timestamp || buildIsoNow();
  const entityVersion = item.entity_version || item.timestamp || queuedAt;

  return {
    sync_item_id: item.id || `${item.table_name}:${item.entity_id}:${queuedAt}`,
    tenant_id: item.tenant_id || DEFAULT_TENANT_ID,
    table_name: item.table_name,
    entity_id: item.entity_id,
    entity_version: entityVersion,
    operation_type: item.operation_type || item.action || 'upsert',
    queued_at: queuedAt,
    sync_status: item.sync_status || 'pending',
    retry_count: item.retry_count || 0,
    data: item.data || {},
    last_error: item.last_error || null
  };
};

class OfflineManager {
  private queue: SyncItem[] = [];

  async init() {
    const storedQueue = await AsyncStorage.getItem(SYNC_QUEUE_KEY);
    if (storedQueue) {
      const parsed = JSON.parse(storedQueue) as LegacySyncItem[];
      this.queue = parsed.map(normalizeQueueItem);
      await this.saveQueue();
    }
  }

  async addToQueue(item: LegacySyncItem) {
    const normalizedItem = normalizeQueueItem(item);
    this.queue.push(normalizedItem);
    await this.saveQueue();
    return normalizedItem;
  }

  async getQueue() {
    return this.queue;
  }

  async clearQueue() {
    this.queue = [];
    await AsyncStorage.removeItem(SYNC_QUEUE_KEY);
  }

  async saveQueue() {
    await AsyncStorage.setItem(SYNC_QUEUE_KEY, JSON.stringify(this.queue));
  }

  private async markRetryScheduled(errorMessage: string) {
    this.queue = this.queue.map((item) => ({
      ...item,
      sync_status: item.sync_status === 'conflict' ? item.sync_status : 'retry_scheduled',
      retry_count: item.sync_status === 'conflict' ? item.retry_count : item.retry_count + 1,
      last_error: errorMessage
    }));
    await this.saveQueue();
  }

  async sync(apiBaseUrl: string, context: string | SyncContext = DEFAULT_DEVICE_ID) {
    const resolvedContext = typeof context === 'string'
      ? { deviceId: context, tenantId: DEFAULT_TENANT_ID }
      : { deviceId: context.deviceId || DEFAULT_DEVICE_ID, tenantId: context.tenantId || DEFAULT_TENANT_ID };

    const pendingItems = this.queue.filter((item) => item.sync_status === 'pending' || item.sync_status === 'retry_scheduled');
    if (pendingItems.length === 0) {
      return { status: 'no_changes', queue_depth: this.queue.length };
    }

    const syncUrl = resolveSyncUrl(apiBaseUrl, `${SYNC_ROUTE_PREFIX}/push`);
    this.queue = this.queue.map((item) => (
      pendingItems.some((pending) => pending.sync_item_id === item.sync_item_id)
        ? { ...item, sync_status: 'syncing' }
        : item
    ));
    await this.saveQueue();

    try {
      const res = await axios.post(syncUrl, {
        tenant_id: resolvedContext.tenantId,
        changes: pendingItems
      }, {
        headers: {
          'x-device-id': resolvedContext.deviceId,
          'x-user-id': resolvedContext.tenantId
        }
      });

      const results = (res.data.results || []) as PushResult[];
      const resultMap = new Map(results.map((result) => [result.sync_item_id, result]));
      const retainedItems: SyncItem[] = [];

      for (const item of this.queue) {
        const result = resultMap.get(item.sync_item_id);
        if (!result) {
          retainedItems.push(item);
          continue;
        }

        if (result.status === 'success') {
          continue;
        }

        retainedItems.push({
          ...item,
          entity_version: result.entity_version || item.entity_version,
          sync_status: result.status === 'conflict' ? 'conflict' : (result.sync_status || 'retry_scheduled'),
          retry_count: result.retry_count ?? (item.retry_count + 1),
          last_error: result.error || null
        });
      }

      this.queue = retainedItems;
      await this.saveQueue();
      return {
        status: 'success',
        results,
        queue_depth: this.queue.length
      };
    } catch (err) {
      const errorMessage = axios.isAxiosError(err)
        ? err.message
        : 'Offline sync failed';
      await this.markRetryScheduled(errorMessage);
      return { status: 'error', error: errorMessage, queue_depth: this.queue.length };
    }
  }

  async pullChanges(apiBaseUrl: string, context: string | SyncContext = DEFAULT_DEVICE_ID) {
    const resolvedContext = typeof context === 'string'
      ? { deviceId: context, tenantId: DEFAULT_TENANT_ID }
      : { deviceId: context.deviceId || DEFAULT_DEVICE_ID, tenantId: context.tenantId || DEFAULT_TENANT_ID };

    const lastSync = await AsyncStorage.getItem(LAST_SYNC_TS_KEY);
    const syncUrl = resolveSyncUrl(apiBaseUrl, `${SYNC_ROUTE_PREFIX}/pull`);

    try {
      const res = await axios.get(syncUrl, {
        params: { since: lastSync || '1970-01-01' },
        headers: {
          'x-device-id': resolvedContext.deviceId,
          'x-user-id': resolvedContext.tenantId
        }
      });

      const serverTimestamp = res.data.server_timestamp || res.data.timestamp || buildIsoNow();
      await AsyncStorage.setItem(LAST_SYNC_TS_KEY, serverTimestamp);
      return Array.isArray(res.data.changes) ? res.data.changes : [];
    } catch (err) {
      console.error('[OfflineManager] Pull failed:', err);
      return [];
    }
  }
}

export const offlineManager = new OfflineManager();
