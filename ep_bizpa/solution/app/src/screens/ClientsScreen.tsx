import React from 'react';
import { ScrollView, Text, View } from 'react-native';
import { Briefcase } from 'lucide-react-native';
import { DEMO_CLIENTS } from '../demoData';
import { styles } from '../styles';
import { ClientItem } from '../types';

interface ClientsScreenProps {
  darkMode: boolean;
  clients: ClientItem[];
}

export function ClientsScreen({ darkMode, clients }: ClientsScreenProps) {
  const visibleClients = clients.length ? clients : DEMO_CLIENTS;

  return (
    <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
      <Text style={[styles.tabTitle, darkMode && styles.textWhite]}>Clients</Text>
      {visibleClients.map((client) => (
        <View key={client.id} style={[styles.listCard, darkMode && styles.cardDark]}>
          <View style={styles.listIcon}>
            <Briefcase size={18} />
          </View>
          <View style={styles.listBody}>
            <Text style={[styles.listTitle, darkMode && styles.textWhite]}>{client.name}</Text>
            <Text style={styles.listMeta}>{client.phone || client.email || 'No contact detail recorded.'}</Text>
          </View>
        </View>
      ))}
    </ScrollView>
  );
}
