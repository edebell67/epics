import React from 'react';
import { ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { AlertCircle, Bell, Briefcase, ChevronRight, Clock3, TrendingUp } from 'lucide-react-native';
import { styles } from '../styles';
import { ClientItem, InboxFilterKey, NotificationItem } from '../types';

interface HomeScreenProps {
  darkMode: boolean;
  inboxCounts: Record<InboxFilterKey, number>;
  inboxError: string | null;
  notifications: NotificationItem[];
  clients: ClientItem[];
  rankedStrategyCount: number;
  onOpenInbox: () => void;
  onOpenNeedsReview: () => void;
  onOpenClients: () => void;
  onOpenLeaderboard: () => void;
}

export function HomeScreen(props: HomeScreenProps) {
  const {
    darkMode,
    inboxCounts,
    inboxError,
    notifications,
    clients,
    rankedStrategyCount,
    onOpenInbox,
    onOpenNeedsReview,
    onOpenClients,
    onOpenLeaderboard,
  } = props;

  return (
    <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
      <View style={[styles.heroCard, darkMode && styles.cardDark]}>
        <Text style={styles.heroEyebrow}>Business Activity Inbox</Text>
        <Text style={styles.heroAmount}>{inboxCounts.all}</Text>
        <Text style={styles.heroSubtitle}>recent business events across quotes, payments, alerts, and review queues.</Text>
        <View style={styles.heroSummaryRow}>
          <View style={styles.heroSummaryItem}>
            <Text style={styles.heroSummaryLabel}>Needs Review</Text>
            <Text style={styles.heroSummaryValue}>{inboxCounts.needs_review}</Text>
          </View>
          <View style={styles.heroSummaryItem}>
            <Text style={styles.heroSummaryLabel}>Payments</Text>
            <Text style={styles.heroSummaryValue}>{inboxCounts.payments}</Text>
          </View>
          <View style={styles.heroSummaryItem}>
            <Text style={styles.heroSummaryLabel}>Alerts</Text>
            <Text style={styles.heroSummaryValue}>{inboxCounts.alerts}</Text>
          </View>
        </View>
      </View>

      {inboxError ? (
        <View style={[styles.noticeCard, darkMode && styles.noticeCardDark]}>
          <AlertCircle size={16} />
          <Text style={[styles.noticeText, darkMode && styles.textWhite]}>{inboxError}</Text>
        </View>
      ) : null}

      <View style={styles.gridWrap}>
        <TouchableOpacity style={[styles.gridItem, darkMode && styles.cardDark]} onPress={onOpenInbox}>
          <Clock3 size={22} />
          <Text style={[styles.gridValue, darkMode && styles.textWhite]}>{inboxCounts.all}</Text>
          <Text style={[styles.gridTitle, darkMode && styles.textWhite]}>Inbox Events</Text>
          <Text style={styles.gridMeta}>Chronological business history</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.gridItem, darkMode && styles.cardDark]} onPress={onOpenNeedsReview}>
          <AlertCircle size={22} />
          <Text style={[styles.gridValue, darkMode && styles.textWhite]}>{inboxCounts.needs_review}</Text>
          <Text style={[styles.gridTitle, darkMode && styles.textWhite]}>Needs Review</Text>
          <Text style={styles.gridMeta}>Operator follow-up queue</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.gridItem, darkMode && styles.cardDark]} onPress={onOpenClients}>
          <Briefcase size={22} />
          <Text style={[styles.gridValue, darkMode && styles.textWhite]}>{clients.length}</Text>
          <Text style={[styles.gridTitle, darkMode && styles.textWhite]}>Clients</Text>
          <Text style={styles.gridMeta}>Linked counterparties and contacts</Text>
        </TouchableOpacity>
        <TouchableOpacity style={[styles.gridItem, darkMode && styles.cardDark]} onPress={onOpenLeaderboard}>
          <TrendingUp size={22} />
          <Text style={[styles.gridValue, darkMode && styles.textWhite]}>{rankedStrategyCount}</Text>
          <Text style={[styles.gridTitle, darkMode && styles.textWhite]}>Leaders</Text>
          <Text style={styles.gridMeta}>Strategy ranking feed</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={[styles.sectionTitle, darkMode && styles.textWhite]}>Recent Attention</Text>
      </View>
      {(notifications.length ? notifications : [{ id: 'fallback', title: 'Open the inbox to review event-level activity.' }]).map((notification) => (
        <TouchableOpacity key={notification.id} style={[styles.listCard, darkMode && styles.cardDark]} onPress={onOpenInbox}>
          <View style={styles.listIcon}>
            <Bell size={18} />
          </View>
          <View style={styles.listBody}>
            <Text style={[styles.listTitle, darkMode && styles.textWhite]}>{notification.title}</Text>
            <Text style={styles.listMeta}>Open the business activity inbox for full event context.</Text>
          </View>
          <ChevronRight size={18} />
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}
