import React, { useEffect, useMemo, useState } from 'react';
import { Alert, SafeAreaView, StatusBar, Text, TextInput, TouchableOpacity, View } from 'react-native';
import axios from 'axios';
import * as Speech from 'expo-speech';
import * as ImagePicker from 'expo-image-picker';
import { ExpoSpeechRecognitionModule, useSpeechRecognitionEvent } from 'expo-speech-recognition';
import { Bell, Briefcase, Clock3, Image as ImageIcon, LayoutGrid, Mic, Moon, RefreshCcw, Sun, TrendingUp } from 'lucide-react-native';
import { offlineManager } from '../OfflineManager';
import { DEMO_CLIENTS, DEMO_INBOX_ITEMS, FINANCIAL_ENTITY_TYPES } from './demoData';
import { ClientsScreen } from './screens/ClientsScreen';
import { EntityScreen } from './screens/EntityScreen';
import { HomeScreen } from './screens/HomeScreen';
import { InboxScreen } from './screens/InboxScreen';
import { LeaderboardScreen } from './screens/LeaderboardScreen';
import { styles } from './styles';
import { CaptureItem, ClientItem, EntityDetailState, InboxFilterKey, InboxItem, InboxResponse, NavKey, NotificationItem, StrategyItem, ThemeMode } from './types';
import { deriveEntityDetail, normalizeEntityDetailResponse } from './utils';

const API_BASE_URL =
  (process.env.EXPO_PUBLIC_BIZPA_API_BASE_URL as string | undefined) || 'http://127.0.0.1:5055/api/v1';
const DEVICE_ID = 'mobile-app-001';
const LEGAL_DISCLAIMER = 'No HMRC submission. Not tax advice.';

export default function BizPAInboxApp() {
  const [theme, setTheme] = useState<ThemeMode>('light');
  const [currentTab, setCurrentTab] = useState<NavKey>('home');
  const [transcript, setTranscript] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [clients, setClients] = useState<ClientItem[]>([]);
  const [strategies, setStrategies] = useState<StrategyItem[]>([]);
  const [items, setItems] = useState<CaptureItem[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);
  const [inboxLoading, setInboxLoading] = useState(true);
  const [inboxError, setInboxError] = useState<string | null>(null);
  const [inboxFilter, setInboxFilter] = useState<InboxFilterKey>('all');
  const [selectedEntity, setSelectedEntity] = useState<EntityDetailState | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);
  const [entityError, setEntityError] = useState<string | null>(null);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [strategiesError, setStrategiesError] = useState<string | null>(null);

  useSpeechRecognitionEvent('result', (event) => setTranscript(event.results[0]?.transcript || ''));
  useSpeechRecognitionEvent('end', () => {
    setIsListening(false);
    if (transcript.trim()) void handleVoiceProcess(transcript);
  });

  useEffect(() => {
    const boot = async () => {
      await offlineManager.init();
      await fetchInitialData();
    };
    void boot();

    const refreshTimer = setInterval(() => void fetchInitialData(), 30000);
    const syncTimer = setInterval(() => void offlineManager.sync(API_BASE_URL, DEVICE_ID), 15000);
    return () => {
      clearInterval(refreshTimer);
      clearInterval(syncTimer);
    };
  }, []);

  const fetchInitialData = async () => {
    await Promise.all([fetchBusinessInbox(inboxFilter), fetchItems(), fetchClients(), fetchNotifications(), fetchStrategies()]);
  };

  const fetchBusinessInbox = async (filter: InboxFilterKey) => {
    setInboxLoading(true);
    try {
      const response = await axios.get<InboxResponse>(`${API_BASE_URL}/business-events/inbox`, { params: { filter, limit: 50 } });
      setInboxItems(Array.isArray(response.data.items) ? response.data.items : []);
      setInboxError(null);
    } catch (error) {
      console.error('Business inbox error:', error);
      setInboxItems(DEMO_INBOX_ITEMS);
      setInboxError('Using local demo inbox data because the backend inbox feed was unavailable.');
    } finally {
      setInboxLoading(false);
    }
  };

  const fetchItems = async () => {
    try {
      const response = await axios.get<CaptureItem[]>(`${API_BASE_URL}/items`);
      setItems(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Items fetch error:', error);
      setItems([]);
    }
  };

  const fetchClients = async () => {
    try {
      const response = await axios.get<ClientItem[]>(`${API_BASE_URL}/clients`);
      setClients(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Clients fetch error:', error);
      setClients(DEMO_CLIENTS);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await axios.get<NotificationItem[]>(`${API_BASE_URL}/notifications`);
      setNotifications(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Notifications fetch error:', error);
      setNotifications([]);
    }
  };

  const fetchStrategies = async () => {
    setStrategiesLoading(true);
    try {
      const response = await axios.get<StrategyItem[]>(`${API_BASE_URL}/strategies`);
      setStrategies(Array.isArray(response.data) ? response.data : []);
      setStrategiesError(null);
    } catch (error) {
      console.error('Strategies fetch error:', error);
      setStrategies([]);
      setStrategiesError('Strategy leaderboard unavailable.');
    } finally {
      setStrategiesLoading(false);
    }
  };

  const handleVoiceProcess = async (text: string) => {
    if (!text.trim()) return;
    try {
      const response = await axios.post(`${API_BASE_URL}/voice/process`, { transcript: text, device_id: DEVICE_ID });
      if (response.data?.confirmation_text) Speech.speak(response.data.confirmation_text);
      await fetchInitialData();
    } catch (error) {
      console.error('Voice processing error:', error);
      Alert.alert('Voice Error', 'Failed to process command.');
    }
  };

  const toggleListening = async () => {
    if (isListening) {
      ExpoSpeechRecognitionModule.stop();
      setIsListening(false);
      return;
    }
    const permission = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('Permission Refused', 'Voice access is required.');
      return;
    }
    setTranscript('');
    setIsListening(true);
    ExpoSpeechRecognitionModule.start({ lang: 'en-GB', interimResults: true, continuous: true });
  };

  const handleImageCapture = async () => {
    const permissionResult = await ImagePicker.requestCameraPermissionsAsync();
    if (!permissionResult.granted) {
      Alert.alert('Permission Refused', 'You need to allow camera access.');
      return;
    }
    const result = await ImagePicker.launchCameraAsync({ allowsEditing: true, aspect: [4, 3], quality: 0.7 });
    if (result.canceled) return;
    Speech.speak('Image captured. Upload integration is available when the local API is running.');
  };

  const openInboxEntity = async (item: InboxItem) => {
    setCurrentTab('entity');
    setEntityLoading(true);
    setEntityError(null);
    try {
      const entityType = item.linked_entity_type || item.linked_entity.type || 'record';
      let captureItem = items.find((existing) => existing.id === item.linked_entity_id) || null;
      let clientRecord = clients.find((client) => client.id === item.linked_entity.counterparty_id) || null;
      if (!captureItem && item.linked_entity_id && FINANCIAL_ENTITY_TYPES.has(entityType)) {
        try {
          const itemResponse = await axios.get<CaptureItem>(`${API_BASE_URL}/items/${item.linked_entity_id}`);
          captureItem = itemResponse.data;
        } catch (error) {
          console.error('Entity item fetch error:', error);
        }
      }

      const clientId = captureItem?.client_id || item.linked_entity.counterparty_id;
      if (!clientRecord && clientId) {
        try {
          const clientResponse = await axios.get<ClientItem>(`${API_BASE_URL}/clients/${clientId}`);
          clientRecord = clientResponse.data;
        } catch (error) {
          console.error('Entity client fetch error:', error);
        }
      }

      if (item.linked_entity_id && FINANCIAL_ENTITY_TYPES.has(entityType)) {
        try {
          const detailResponse = await axios.get(`${API_BASE_URL}/business-events/entity-view/${entityType}/${item.linked_entity_id}`);
          setSelectedEntity(normalizeEntityDetailResponse(detailResponse.data, deriveEntityDetail(item, captureItem, clientRecord)));
          return;
        } catch (error) {
          console.error('Entity detail fetch error:', error);
        }
      }

      setSelectedEntity(deriveEntityDetail(item, captureItem, clientRecord));
    } catch (error) {
      console.error('Open entity error:', error);
      setEntityError('Unable to load the linked entity detail.');
      setSelectedEntity(deriveEntityDetail(item, null, null));
    } finally {
      setEntityLoading(false);
    }
  };

  const inboxCounts = useMemo(
    () => ({
      all: inboxItems.filter((item) => item.filter_tags.includes('all')).length,
      needs_review: inboxItems.filter((item) => item.filter_tags.includes('needs_review')).length,
      financial: inboxItems.filter((item) => item.filter_tags.includes('financial')).length,
      quotes: inboxItems.filter((item) => item.filter_tags.includes('quotes')).length,
      payments: inboxItems.filter((item) => item.filter_tags.includes('payments')).length,
      alerts: inboxItems.filter((item) => item.filter_tags.includes('alerts')).length,
    }),
    [inboxItems]
  );

  const rankedStrategies = useMemo(
    () =>
      [...strategies].sort((left, right) => {
        const leftRank = Number(left.rank ?? left.position ?? left.leaderboard_rank ?? Number.MAX_SAFE_INTEGER);
        const rightRank = Number(right.rank ?? right.position ?? right.leaderboard_rank ?? Number.MAX_SAFE_INTEGER);
        if (leftRank !== rightRank) return leftRank - rightRank;
        const leftScore = Number(left.score ?? left.pnl ?? left.return_pct ?? left.win_rate ?? Number.NEGATIVE_INFINITY);
        const rightScore = Number(right.score ?? right.pnl ?? right.return_pct ?? right.win_rate ?? Number.NEGATIVE_INFINITY);
        return rightScore - leftScore;
      }),
    [strategies]
  );

  const darkMode = theme === 'dark';

  return (
    <SafeAreaView style={[styles.safeArea, darkMode && styles.safeAreaDark]}>
      <StatusBar barStyle={darkMode ? 'light-content' : 'dark-content'} />
      <View style={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.logo}>bizPA Inbox</Text>
            <Text style={styles.logoSub}>Local API: {API_BASE_URL}</Text>
          </View>
          <View style={styles.headerIcons}>
            <TouchableOpacity onPress={() => setTheme((previous) => (previous === 'light' ? 'dark' : 'light'))} style={styles.iconButton}>
              {darkMode ? <Sun size={22} /> : <Moon size={22} />}
            </TouchableOpacity>
            <TouchableOpacity onPress={() => void fetchInitialData()} style={styles.iconButton}>
              <RefreshCcw size={22} />
            </TouchableOpacity>
            <View style={styles.iconButton}>
              <Bell size={22} />
            </View>
          </View>
        </View>

        <Text style={styles.disclaimer}>{LEGAL_DISCLAIMER}</Text>

        {currentTab === 'home' && (
          <HomeScreen
            darkMode={darkMode}
            inboxCounts={inboxCounts}
            inboxError={inboxError}
            notifications={notifications}
            clients={clients}
            rankedStrategyCount={rankedStrategies.length}
            onOpenInbox={() => setCurrentTab('inbox')}
            onOpenNeedsReview={() => {
              setInboxFilter('needs_review');
              void fetchBusinessInbox('needs_review');
              setCurrentTab('inbox');
            }}
            onOpenClients={() => setCurrentTab('clients')}
            onOpenLeaderboard={() => setCurrentTab('leaderboard')}
          />
        )}
        {currentTab === 'inbox' && (
          <InboxScreen
            darkMode={darkMode}
            inboxFilter={inboxFilter}
            inboxCounts={inboxCounts}
            inboxItems={inboxItems}
            inboxLoading={inboxLoading}
            onRefresh={() => void fetchBusinessInbox(inboxFilter)}
            onChangeFilter={(filter) => {
              setInboxFilter(filter);
              void fetchBusinessInbox(filter);
            }}
            onOpenEntity={(item) => void openInboxEntity(item)}
          />
        )}
        {currentTab === 'clients' && <ClientsScreen darkMode={darkMode} clients={clients} />}
        {currentTab === 'leaderboard' && (
          <LeaderboardScreen
            darkMode={darkMode}
            rankedStrategies={rankedStrategies}
            strategiesLoading={strategiesLoading}
            strategiesError={strategiesError}
          />
        )}
        {currentTab === 'entity' && (
          <EntityScreen
            darkMode={darkMode}
            selectedEntity={selectedEntity}
            entityLoading={entityLoading}
            entityError={entityError}
            onBack={() => setCurrentTab('inbox')}
          />
        )}

        <View style={[styles.bottomNav, darkMode && styles.bottomNavDark]}>
          {[
            { key: 'home' as const, label: 'Home', icon: LayoutGrid },
            { key: 'inbox' as const, label: 'Inbox', icon: Clock3 },
            { key: 'clients' as const, label: 'Clients', icon: Briefcase },
            { key: 'leaderboard' as const, label: 'Leaders', icon: TrendingUp },
          ].map((nav) => {
            const Icon = nav.icon;
            const active = currentTab === nav.key;
            return (
              <TouchableOpacity key={nav.key} style={styles.navItem} onPress={() => setCurrentTab(nav.key)}>
                <Icon size={22} />
                <Text style={[styles.navLabel, { color: active ? '#0f766e' : darkMode ? '#cbd5e1' : '#64748b' }]}>{nav.label}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <View style={[styles.voiceBar, darkMode && styles.voiceBarDark]}>
          <TouchableOpacity style={styles.actionButton} onPress={() => void handleImageCapture()}>
            <ImageIcon size={22} />
          </TouchableOpacity>
          <TextInput
            style={[styles.input, darkMode && styles.inputDark]}
            placeholder="Speak or type a quick action"
            placeholderTextColor={darkMode ? '#94a3b8' : '#64748b'}
            value={transcript}
            onChangeText={setTranscript}
            onSubmitEditing={() => void handleVoiceProcess(transcript)}
          />
          <TouchableOpacity style={[styles.micButton, isListening && styles.micButtonActive]} onPress={() => void toggleListening()}>
            <Mic size={24} />
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}
