import React from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';
import { AlertCircle } from 'lucide-react-native';
import { styles } from '../styles';
import { StrategyItem } from '../types';

interface LeaderboardScreenProps {
  darkMode: boolean;
  rankedStrategies: StrategyItem[];
  strategiesLoading: boolean;
  strategiesError: string | null;
}

export function LeaderboardScreen(props: LeaderboardScreenProps) {
  const { darkMode, rankedStrategies, strategiesLoading, strategiesError } = props;

  return (
    <ScrollView style={styles.scrollContainer} showsVerticalScrollIndicator={false}>
      <Text style={[styles.tabTitle, darkMode && styles.textWhite]}>Strategy Leaderboard</Text>
      {strategiesLoading ? (
        <View style={[styles.stateCard, darkMode && styles.cardDark]}>
          <ActivityIndicator size="small" color="#2563eb" />
          <Text style={styles.stateText}>Loading strategies...</Text>
        </View>
      ) : null}
      {!strategiesLoading && strategiesError ? (
        <View style={[styles.noticeCard, darkMode && styles.noticeCardDark]}>
          <AlertCircle size={16} />
          <Text style={[styles.noticeText, darkMode && styles.textWhite]}>{strategiesError}</Text>
        </View>
      ) : null}
      {!strategiesLoading &&
        !strategiesError &&
        rankedStrategies.map((strategy, index) => {
          const rank = Number(strategy.rank ?? strategy.position ?? strategy.leaderboard_rank ?? index + 1);
          const score = Number(strategy.score ?? strategy.pnl ?? strategy.return_pct ?? strategy.win_rate ?? 0);
          return (
            <View key={strategy.id || strategy.name || `strategy-${index}`} style={[styles.listCard, darkMode && styles.cardDark]}>
              <View style={styles.rankPill}>
                <Text style={styles.rankPillText}>#{rank}</Text>
              </View>
              <View style={styles.listBody}>
                <Text style={[styles.listTitle, darkMode && styles.textWhite]}>
                  {strategy.name || strategy.strategy_name || strategy.title || `Strategy ${index + 1}`}
                </Text>
                <Text style={styles.listMeta}>
                  {strategy.description || strategy.market || strategy.symbol || strategy.timeframe || strategy.category || 'Live strategy'}
                </Text>
              </View>
              <Text style={[styles.scoreText, darkMode && styles.textWhite]}>{score >= 0 ? `+${score.toFixed(2)}` : score.toFixed(2)}</Text>
            </View>
          );
        })}
    </ScrollView>
  );
}
