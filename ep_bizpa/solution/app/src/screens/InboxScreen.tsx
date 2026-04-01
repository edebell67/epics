import React from 'react';
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { ChevronRight, Clock3, FileText, Receipt, RefreshCcw, Search } from 'lucide-react-native';
import { INBOX_FILTERS, TONE_STYLES } from '../demoData';
import { styles } from '../styles';
import { InboxBadge, InboxFilterKey, InboxItem } from '../types';
import { formatDateTime, formatMoney, titleCase } from '../utils';

interface InboxScreenProps {
  darkMode: boolean;
  inboxFilter: InboxFilterKey;
  inboxCounts: Record<InboxFilterKey, number>;
  inboxItems: InboxItem[];
  inboxLoading: boolean;
  onRefresh: () => void;
  onChangeFilter: (filter: InboxFilterKey) => void;
  onOpenEntity: (item: InboxItem) => void;
}

export function InboxScreen(props: InboxScreenProps) {
  const { darkMode, inboxFilter, inboxCounts, inboxItems, inboxLoading, onRefresh, onChangeFilter, onOpenEntity } = props;

  const renderBadge = (badge: InboxBadge, index: number) => (
    <View key={`${badge.label}-${index}`} style={[styles.badge, { backgroundColor: TONE_STYLES[badge.tone].backgroundColor }]}>
      <Text style={[styles.badgeText, { color: TONE_STYLES[badge.tone].color }]}>{badge.label}</Text>
    </View>
  );

  return (
    <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={[styles.tabTitle, darkMode && styles.textWhite]}>Business Activity Inbox</Text>
          <Text style={styles.sectionMeta}>Immutable event history with operator-friendly filters and linked entities.</Text>
        </View>
        <TouchableOpacity style={[styles.refreshChip, darkMode && styles.refreshChipDark]} onPress={onRefresh}>
          <RefreshCcw size={16} />
          <Text style={[styles.refreshChipText, darkMode && styles.textWhite]}>Refresh</Text>
        </TouchableOpacity>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterRow} contentContainerStyle={styles.filterRowContent}>
        {INBOX_FILTERS.map((filter) => {
          const active = inboxFilter === filter.key;
          return (
            <TouchableOpacity
              key={filter.key}
              style={[styles.filterChip, active && styles.filterChipActive, darkMode && !active && styles.filterChipDark]}
              onPress={() => onChangeFilter(filter.key)}
            >
              <Text style={[styles.filterChipText, active && styles.filterChipTextActive, darkMode && !active && styles.textWhite]}>
                {filter.label}
              </Text>
              <View style={[styles.filterCountPill, active && styles.filterCountPillActive]}>
                <Text style={[styles.filterCountText, active && styles.filterCountTextActive]}>{inboxCounts[filter.key]}</Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </ScrollView>

      {inboxLoading ? (
        <View style={[styles.stateCard, darkMode && styles.cardDark]}>
          <ActivityIndicator size="small" color="#0f766e" />
          <Text style={styles.stateText}>Loading inbox events...</Text>
        </View>
      ) : null}

      {!inboxLoading && inboxItems.length === 0 ? (
        <View style={[styles.stateCard, darkMode && styles.cardDark]}>
          <Search size={20} />
          <Text style={styles.stateText}>No business events returned for this filter.</Text>
        </View>
      ) : null}

      {inboxItems.map((item) => {
        const badges = [item.needs_review_badge, item.status_badge, item.auto_commit_badge].filter(Boolean) as InboxBadge[];
        return (
          <TouchableOpacity key={item.event_id} style={[styles.inboxCard, darkMode && styles.cardDark]} onPress={() => onOpenEntity(item)}>
            <View style={styles.inboxCardHeader}>
              <View style={styles.eventIconWrap}>
                {item.linked_entity_type === 'payment' ? (
                  <Receipt size={18} />
                ) : item.linked_entity_type === 'quote' ? (
                  <FileText size={18} />
                ) : (
                  <Clock3 size={18} />
                )}
              </View>
              <View style={styles.inboxCardTitleWrap}>
                <Text style={[styles.inboxTitle, darkMode && styles.textWhite]}>{titleCase(item.event_title)}</Text>
                <Text style={styles.inboxMeta}>
                  {formatDateTime(item.timestamp)} • {titleCase(item.source_type || 'system')}
                </Text>
              </View>
              <ChevronRight size={18} />
            </View>

            <View style={styles.badgeRow}>{badges.map((badge, index) => renderBadge(badge, index))}</View>

            <View style={styles.inboxDetailGrid}>
              <View style={styles.inboxDetailItem}>
                <Text style={styles.inboxDetailLabel}>Entity</Text>
                <Text style={[styles.inboxDetailValue, darkMode && styles.textWhite]}>{titleCase(item.linked_entity_type || item.linked_entity.type || 'record')}</Text>
              </View>
              <View style={styles.inboxDetailItem}>
                <Text style={styles.inboxDetailLabel}>Reference</Text>
                <Text style={[styles.inboxDetailValue, darkMode && styles.textWhite]}>{item.linked_entity.reference_number || item.quarter_reference || 'None'}</Text>
              </View>
              <View style={styles.inboxDetailItem}>
                <Text style={styles.inboxDetailLabel}>Counterparty</Text>
                <Text style={[styles.inboxDetailValue, darkMode && styles.textWhite]}>{item.counterparty || item.linked_entity.counterparty_name || 'Not linked'}</Text>
              </View>
              <View style={styles.inboxDetailItem}>
                <Text style={styles.inboxDetailLabel}>Amount</Text>
                <Text style={[styles.inboxDetailValue, darkMode && styles.textWhite]}>{formatMoney(item.amount) || 'N/A'}</Text>
              </View>
            </View>

            {item.description ? <Text style={styles.inboxDescription}>{item.description}</Text> : null}
          </TouchableOpacity>
        );
      })}
    </ScrollView>
  );
}
