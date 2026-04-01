import React from 'react';
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { AlertCircle, ChevronRight } from 'lucide-react-native';
import { TONE_STYLES } from '../demoData';
import { styles } from '../styles';
import { EntityDetailState } from '../types';
import { formatDateTime, titleCase } from '../utils';

interface EntityScreenProps {
  darkMode: boolean;
  selectedEntity: EntityDetailState | null;
  entityLoading: boolean;
  entityError: string | null;
  onBack: () => void;
}

export function EntityScreen(props: EntityScreenProps) {
  const { darkMode, selectedEntity, entityLoading, entityError, onBack } = props;

  return (
    <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
      <TouchableOpacity style={styles.backRow} onPress={onBack}>
        <ChevronRight size={18} />
        <Text style={styles.backText}>Back to inbox</Text>
      </TouchableOpacity>

      {entityLoading ? (
        <View style={[styles.stateCard, darkMode && styles.cardDark]}>
          <ActivityIndicator size="small" color="#0f766e" />
          <Text style={styles.stateText}>Loading linked entity...</Text>
        </View>
      ) : null}

      {!entityLoading && selectedEntity ? (
        <>
          <View style={[styles.entityHeroCard, darkMode && styles.cardDark]}>
            <Text style={styles.entityEyebrow}>{titleCase(selectedEntity.type)}</Text>
            <Text style={[styles.entityTitle, darkMode && styles.textWhite]}>{selectedEntity.headerBlock.title}</Text>
            <Text style={styles.entitySubtitle}>{selectedEntity.headerBlock.subtitle}</Text>
            <View style={styles.entityHeroMeta}>
              {selectedEntity.status ? (
                <View style={[styles.badge, { backgroundColor: TONE_STYLES.info.backgroundColor }]}>
                  <Text style={[styles.badgeText, { color: TONE_STYLES.info.color }]}>{titleCase(selectedEntity.status)}</Text>
                </View>
              ) : null}
              {selectedEntity.paymentStatus ? (
                <View style={[styles.badge, { backgroundColor: '#fef3c7' }]}>
                  <Text style={[styles.badgeText, { color: '#92400e' }]}>{titleCase(selectedEntity.paymentStatus)}</Text>
                </View>
              ) : null}
              {selectedEntity.amount ? (
                <View style={[styles.badge, { backgroundColor: '#d1fae5' }]}>
                  <Text style={[styles.badgeText, { color: '#065f46' }]}>{selectedEntity.amount}</Text>
                </View>
              ) : null}
              {selectedEntity.correctionState ? (
                <View style={[styles.badge, { backgroundColor: '#e2e8f0' }]}>
                  <Text style={[styles.badgeText, { color: '#334155' }]}>{titleCase(selectedEntity.correctionState)}</Text>
                </View>
              ) : null}
            </View>
            {selectedEntity.headerBlock.labels.length ? (
              <View style={styles.entityTagRow}>
                {selectedEntity.headerBlock.labels.map((label) => (
                  <View key={label} style={styles.entityTag}>
                    <Text style={styles.entityTagText}>{label}</Text>
                  </View>
                ))}
              </View>
            ) : null}
          </View>

          {entityError ? (
            <View style={[styles.noticeCard, darkMode && styles.noticeCardDark]}>
              <AlertCircle size={16} />
              <Text style={[styles.noticeText, darkMode && styles.textWhite]}>{entityError}</Text>
            </View>
          ) : null}

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Summary</Text>
            <Text style={styles.entitySummaryText}>{selectedEntity.headerBlock.description}</Text>
          </View>

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Counterparty</Text>
            <View style={styles.entityFieldRow}>
              <Text style={styles.entityFieldLabel}>Name</Text>
              <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{selectedEntity.counterparty.name || 'Not linked'}</Text>
            </View>
            {selectedEntity.counterparty.email ? (
              <View style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>Email</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{selectedEntity.counterparty.email}</Text>
              </View>
            ) : null}
            {selectedEntity.counterparty.phone ? (
              <View style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>Phone</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{selectedEntity.counterparty.phone}</Text>
              </View>
            ) : null}
          </View>

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Amounts</Text>
            {selectedEntity.moneyBreakdown.net_amount ? (
              <View style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>Net</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{selectedEntity.moneyBreakdown.net_amount}</Text>
              </View>
            ) : null}
            {selectedEntity.moneyBreakdown.vat_amount ? (
              <View style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>VAT</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{selectedEntity.moneyBreakdown.vat_amount}</Text>
              </View>
            ) : null}
            {selectedEntity.moneyBreakdown.gross_amount ? (
              <View style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>Gross</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{selectedEntity.moneyBreakdown.gross_amount}</Text>
              </View>
            ) : null}
            {selectedEntity.dueDate ? (
              <View style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>Due Date</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{formatDateTime(selectedEntity.dueDate)}</Text>
              </View>
            ) : null}
          </View>

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Fields</Text>
            {selectedEntity.fields.map((field) => (
              <View key={`${field.label}-${field.value}`} style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>{field.label}</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{field.value}</Text>
              </View>
            ))}
          </View>

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Attachments</Text>
            {selectedEntity.attachments.length ? selectedEntity.attachments.map((attachment) => (
              <View key={attachment.id} style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>{titleCase(attachment.kind)}</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{attachment.file_path}</Text>
              </View>
            )) : <Text style={styles.entitySummaryText}>No attachments linked to this entity.</Text>}
          </View>

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Notes</Text>
            {selectedEntity.notes.length ? selectedEntity.notes.map((note) => (
              <View key={`${note.kind}-${note.created_at || note.text}`} style={styles.entityFieldRow}>
                <Text style={styles.entityFieldLabel}>{titleCase(note.kind)}</Text>
                <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{note.text}</Text>
              </View>
            )) : <Text style={styles.entitySummaryText}>No notes linked to this entity.</Text>}
          </View>

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Entity Timeline</Text>
            {selectedEntity.timeline.length ? selectedEntity.timeline.map((event) => (
              <View key={event.event_id} style={styles.entityTimelineRow}>
                <View style={styles.entityTimelineDot} />
                <View style={styles.entityTimelineBody}>
                  <Text style={[styles.entityFieldValue, darkMode && styles.textWhite]}>{titleCase(event.event_type)}</Text>
                  <Text style={styles.entityTimelineMeta}>{formatDateTime(event.created_at)}{event.source_type ? ` • ${titleCase(event.source_type)}` : ''}</Text>
                  {event.description ? <Text style={styles.entitySummaryText}>{event.description}</Text> : null}
                </View>
              </View>
            )) : <Text style={styles.entitySummaryText}>No timeline events found for this entity.</Text>}
          </View>

          <View style={[styles.entitySummaryCard, darkMode && styles.cardDark]}>
            <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Available Actions</Text>
            <View style={styles.entityActionWrap}>
              {selectedEntity.availableActions.length ? selectedEntity.availableActions.map((action) => (
                <View key={action} style={styles.entityActionChip}>
                  <Text style={styles.entityActionText}>{action}</Text>
                </View>
              )) : <Text style={styles.entitySummaryText}>No suggested actions for this entity.</Text>}
            </View>
          </View>
        </>
      ) : null}
    </ScrollView>
  );
}
