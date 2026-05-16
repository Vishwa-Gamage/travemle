import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, ScrollView, Alert, ActivityIndicator } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/context/AuthContext';
import { ENDPOINTS } from '@/constants/config';
import { INTERESTS } from '@/constants/interests';
import api from '@/services/api';

const TRAVEL_MODES = ['Car', 'Bus', 'Train'] as const;

interface InsightInterest { interest: string; trips: number; percentage: number; }
interface Insights {
  status:         string;
  total_trips?:   number;
  top_interests?: InsightInterest[];
  preferred_mode?:string;
  avg_budget?:    number;
  budget_trend?:  string;
  most_visited?:  string | null;
  insight?:       string;
  message?:       string;
}

export default function ProfileScreen() {
  const { user, refreshUser, logout } = useAuth();
  
  const [budget, setBudget] = useState('20000');
  const [selectedInterests, setSelectedInterests] = useState<string[]>([]);
  const [selectedMode, setSelectedMode] = useState<string>('Bus');
  const [loading, setLoading] = useState(false);
  const [insights, setInsights] = useState<Insights | null>(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  
  useEffect(() => {
    if (user?.profile) {
      setBudget(user.profile.default_budget.toString());
      setSelectedMode(user.profile.default_travel_mode);
      if (user.profile.interests_csv) {
        setSelectedInterests(user.profile.interests_csv.split(',').map((s: string) => s.trim()));
      }
    }
    // Auto-fetch behavioural insights from trip history
    fetchInsights();
  }, [user]);

  const fetchInsights = async () => {
    setInsightsLoading(true);
    try {
      const res = await api.get(ENDPOINTS.insights);
      setInsights(res.data);
    } catch (e) {
      console.error('Could not load insights:', e);
    } finally {
      setInsightsLoading(false);
    }
  };

  const toggleInterest = (interest: string) => {
    setSelectedInterests(prev =>
      prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]
    );
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      const payload = {
        default_budget: parseInt(budget) || 20000,
        default_travel_mode: selectedMode,
        interests_csv: selectedInterests.join(', '),
      };
      
      await api.put(ENDPOINTS.me, payload);
      // FIX (BUG-01): refreshUser() fetches the updated user from the server
      // and persists it, keeping local state and AsyncStorage in sync.
      await refreshUser();
      Alert.alert('Success', 'Profile updated successfully!');
    } catch (err: any) {
      Alert.alert('Error', 'Failed to update profile.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>My Profile</Text>
        <TouchableOpacity onPress={logout}>
          <Ionicons name="log-out-outline" size={24} color="#ff3b30" />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.card}>
          <Ionicons name="person-circle-outline" size={60} color="#007AFF" />
          <Text style={styles.username}>{user?.username}</Text>
          <Text style={styles.email}>{user?.email}</Text>
        </View>

        <Text style={styles.sectionTitle}>Default Travel Preferences</Text>

        {/* Default Budget */}
        <Text style={styles.label}>Default Budget (LKR)</Text>
        <View style={styles.inputContainer}>
          <Ionicons name="wallet-outline" size={20} color="#666" style={styles.icon} />
          <TextInput
            style={styles.input}
            value={budget}
            onChangeText={setBudget}
            keyboardType="numeric"
            placeholder="e.g. 20000"
          />
        </View>

        {/* Travel Mode */}
        <Text style={styles.label}>Preferred Travel Mode</Text>
        <View style={styles.modesContainer}>
          {TRAVEL_MODES.map((mode) => {
            const sel = selectedMode === mode;
            const icon = mode === 'Car' ? 'car-sport-outline' : mode === 'Bus' ? 'bus-outline' : 'train-outline';
            return (
              <TouchableOpacity
                key={mode}
                style={[styles.modeButton, sel && styles.modeButtonSelected]}
                onPress={() => setSelectedMode(mode)}
              >
                <Ionicons name={icon} size={28} color={sel ? '#007AFF' : '#666'} />
                <Text style={[styles.modeText, sel && styles.modeTextSelected]}>{mode}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Interests */}
        <Text style={styles.label}>Interests</Text>
        <View style={styles.chipsContainer}>
          {INTERESTS.map((item) => {
            const sel = selectedInterests.includes(item);
            return (
              <TouchableOpacity
                key={item}
                style={[styles.chip, sel && styles.chipSelected]}
                onPress={() => toggleInterest(item)}
              >
                <Text style={[styles.chipText, sel && styles.chipTextSelected]}>{item}</Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <TouchableOpacity style={styles.saveButton} onPress={handleSave} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>Save Preferences</Text>}
        </TouchableOpacity>

        {/* ── Behavioural Insights Panel ──────────────────────────────── */}
        <Text style={[styles.sectionTitle, { marginTop: 28 }]}>📊 Your Travel Insights</Text>
        <Text style={styles.insightSubtitle}>Auto-analyzed from your trip history</Text>

        {insightsLoading ? (
          <ActivityIndicator color="#007AFF" style={{ marginTop: 12 }} />
        ) : !insights || insights.status === 'no_history' ? (
          <View style={styles.insightEmpty}>
            <Ionicons name="analytics-outline" size={36} color="#ccc" />
            <Text style={styles.insightEmptyText}>Plan your first trip to unlock personalized insights!</Text>
          </View>
        ) : (
          <View style={styles.insightCard}>
            {/* Summary Insight */}
            <View style={styles.insightHighlight}>
              <Ionicons name="bulb-outline" size={18} color="#f59e0b" />
              <Text style={styles.insightHighlightText}>{insights.insight}</Text>
            </View>

            {/* Stats Row */}
            <View style={styles.statsRow}>
              <View style={styles.statBox}>
                <Text style={styles.statValue}>{insights.total_trips}</Text>
                <Text style={styles.statLabel}>Trips Planned</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={styles.statValue}>LKR {(insights.avg_budget || 0).toLocaleString()}</Text>
                <Text style={styles.statLabel}>Avg Budget</Text>
              </View>
              <View style={styles.statBox}>
                <Text style={styles.statValue}>{insights.preferred_mode}</Text>
                <Text style={styles.statLabel}>Fav Mode</Text>
              </View>
            </View>

            {/* Top Interests */}
            {insights.top_interests && insights.top_interests.length > 0 && (
              <View style={styles.interestSection}>
                <Text style={styles.insightSectionLabel}>Top Interests (from history)</Text>
                {insights.top_interests.map((item, i) => (
                  <View key={i} style={styles.interestBar}>
                    <View style={styles.interestBarLabelRow}>
                      <Text style={styles.interestBarLabel}>{item.interest}</Text>
                      <Text style={styles.interestBarPct}>{item.percentage}%</Text>
                    </View>
                    <View style={styles.interestBarBg}>
                      <View style={[styles.interestBarFill, { width: `${item.percentage}%` }]} />
                    </View>
                  </View>
                ))}
              </View>
            )}

            {/* Budget Trend */}
            <View style={styles.trendRow}>
              <Ionicons name="trending-up-outline" size={16} color="#007AFF" />
              <Text style={styles.trendText}>Budget Trend: {insights.budget_trend}</Text>
            </View>

            {insights.most_visited && (
              <View style={styles.trendRow}>
                <Ionicons name="location-outline" size={16} color="#007AFF" />
                <Text style={styles.trendText}>Most visited: {insights.most_visited}</Text>
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  header: {
    paddingTop: 60, paddingBottom: 15, paddingHorizontal: 20,
    backgroundColor: '#fff', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    borderBottomWidth: 1, borderBottomColor: '#eee',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#333' },
  content: { padding: 20 },
  card: {
    backgroundColor: '#fff', borderRadius: 16, padding: 20, alignItems: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 5, elevation: 2,
    marginBottom: 24,
  },
  username: { fontSize: 20, fontWeight: '600', color: '#111', marginTop: 10 },
  email: { fontSize: 14, color: '#666', marginTop: 4 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 15 },
  label: { fontSize: 14, fontWeight: '500', color: '#444', marginBottom: 8, marginTop: 10 },
  inputContainer: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    borderRadius: 12, borderWidth: 1, borderColor: '#ddd', paddingHorizontal: 14, height: 50,
    marginBottom: 15,
  },
  input: { flex: 1, fontSize: 16, color: '#000' },
  icon: { marginRight: 10 },
  modesContainer: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 20 },
  modeButton: {
    width: '30%', backgroundColor: '#fff', padding: 15, borderRadius: 12,
    alignItems: 'center', borderWidth: 1, borderColor: '#ddd',
  },
  modeButtonSelected: { borderColor: '#007AFF', backgroundColor: '#eff6ff', borderWidth: 2 },
  modeText: { marginTop: 5, fontSize: 12, color: '#666', fontWeight: '600' },
  modeTextSelected: { color: '#007AFF' },
  chipsContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 30 },
  chip: {
    paddingVertical: 8, paddingHorizontal: 16, borderRadius: 20,
    backgroundColor: '#fff', borderWidth: 1, borderColor: '#ddd',
  },
  chipSelected: { backgroundColor: '#007AFF', borderColor: '#007AFF' },
  chipText: { color: '#555', fontWeight: '500' },
  chipTextSelected: { color: '#fff' },
  saveButton: {
    backgroundColor: '#007AFF', padding: 16, borderRadius: 12, alignItems: 'center',
    shadowColor: '#007AFF', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 5, elevation: 4,
  },
  saveButtonText: { color: '#fff', fontSize: 16, fontWeight: '700' },

  // Insights Panel
  insightSubtitle:     { fontSize: 12, color: '#999', marginBottom: 12, marginTop: -10 },
  insightEmpty: {
    backgroundColor: '#f8f9fa', borderRadius: 14, padding: 24,
    alignItems: 'center', gap: 10, marginBottom: 20,
  },
  insightEmptyText: { color: '#bbb', fontSize: 13, textAlign: 'center' },
  insightCard: {
    backgroundColor: '#1a1a2e', borderRadius: 16, padding: 18, marginBottom: 20,
    shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 10, elevation: 6,
  },
  insightHighlight: {
    flexDirection: 'row', gap: 8, alignItems: 'flex-start',
    backgroundColor: 'rgba(245,158,11,0.12)', borderRadius: 10, padding: 12, marginBottom: 16,
    borderLeftWidth: 3, borderLeftColor: '#f59e0b',
  },
  insightHighlightText: { color: '#e2e8f0', fontSize: 13, lineHeight: 19, flex: 1 },
  statsRow:   { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 18, gap: 8 },
  statBox: {
    flex: 1, backgroundColor: 'rgba(255,255,255,0.07)', borderRadius: 10,
    padding: 12, alignItems: 'center',
  },
  statValue: { color: '#4ade80', fontSize: 14, fontWeight: '800', marginBottom: 2, textAlign: 'center' },
  statLabel: { color: '#94a3b8', fontSize: 10, textAlign: 'center' },
  interestSection:   { marginBottom: 14 },
  insightSectionLabel: { color: '#94a3b8', fontSize: 11, fontWeight: '700', textTransform: 'uppercase', marginBottom: 10, letterSpacing: 0.5 },
  interestBar:       { marginBottom: 10 },
  interestBarLabelRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  interestBarLabel:  { color: '#e2e8f0', fontSize: 13, fontWeight: '600' },
  interestBarPct:    { color: '#60a5fa', fontSize: 12, fontWeight: '700' },
  interestBarBg:     { height: 6, backgroundColor: '#334155', borderRadius: 3, overflow: 'hidden' },
  interestBarFill:   { height: '100%', backgroundColor: '#007AFF', borderRadius: 3 },
  trendRow:          { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  trendText:         { color: '#94a3b8', fontSize: 12, flex: 1 },
});
