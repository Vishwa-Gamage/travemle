import React, { useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, Alert, RefreshControl, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useFocusEffect } from 'expo-router';

import { useAuth } from '@/context/AuthContext';
import { ENDPOINTS } from '@/constants/config';
import api from '@/services/api';

interface Activity {
  day: string;
  time: string;
  location_name: string;
  description: string;
}

interface TripPlan {
  id: number;
  origin: string;
  destination_city: string;
  destination_country: string;
  start_date: string;
  end_date: string;
  interests: string;
  budget: number;
  travel_mode: string;
  plan_json: {
    title: string;
    activities: Activity[];
    budget_breakdown: Record<string, any>;
  };
  weather_summary: string;
  map_url: string;
  created_at: string;
  duration_days: number;
}

export default function HistoryScreen() {
  const router = useRouter();
  const { tokens } = useAuth();
  const [trips, setTrips] = useState<TripPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.get(ENDPOINTS.tripHistory);
      setTrips(res.data);
    } catch (e) {
      console.error('Failed to load history:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Reload whenever this tab comes into focus
  useFocusEffect(useCallback(() => { fetchHistory(); }, [fetchHistory]));

  const handleDelete = (id: number) => {
    Alert.alert('Delete Trip', 'Are you sure you want to delete this trip?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          try {
            // Use the typed endpoint helper — no more fragile string manipulation
            await api.delete(ENDPOINTS.tripHistoryDetail(id));
            setTrips(prev => prev.filter(t => t.id !== id));
          } catch {
            Alert.alert('Error', 'Could not delete trip.');
          }
        },
      },
    ]);
  };

  const viewTrip = (trip: TripPlan) => {
    router.push({
      pathname: '/result',
      params: {
        data: JSON.stringify(trip.plan_json),
        weather: trip.weather_summary,
        map_url: trip.map_url,
      },
    });
  };

  const getModeIcon = (mode: string) => {
    if (mode === 'Car') return 'car-sport-outline';
    if (mode === 'Bus') return 'bus-outline';
    return 'train-outline';
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const renderTrip = ({ item }: { item: TripPlan }) => (
    <TouchableOpacity style={styles.card} onPress={() => viewTrip(item)} activeOpacity={0.85}>
      <View style={styles.cardTop}>
        <View style={styles.cardMain}>
          <Text style={styles.tripTitle} numberOfLines={1}>{item.plan_json?.title || 'Trip Plan'}</Text>
          <View style={styles.routeRow}>
            <Text style={styles.routeText}>{item.origin}</Text>
            <Ionicons name="arrow-forward" size={14} color="#007AFF" style={{ marginHorizontal: 4 }} />
            <Text style={styles.routeText}>{item.destination_city}, {item.destination_country}</Text>
          </View>
        </View>
        <TouchableOpacity onPress={() => handleDelete(item.id)} style={styles.deleteBtn}>
          <Ionicons name="trash-outline" size={18} color="#ff3b30" />
        </TouchableOpacity>
      </View>

      <View style={styles.metaRow}>
        <View style={styles.metaItem}>
          <Ionicons name="calendar-outline" size={13} color="#888" />
          <Text style={styles.metaText}>{formatDate(item.start_date)} - {formatDate(item.end_date)}</Text>
        </View>
        <View style={styles.metaItem}>
          <Ionicons name={getModeIcon(item.travel_mode)} size={13} color="#888" />
          <Text style={styles.metaText}>{item.travel_mode}</Text>
        </View>
      </View>

      <View style={styles.bottomRow}>
        <View style={styles.durationBadge}>
          <Ionicons name="time-outline" size={12} color="#007AFF" />
          <Text style={styles.durationText}>{item.duration_days} days</Text>
        </View>
        <Text style={styles.budget}>LKR {item.budget.toLocaleString()}</Text>
        <View style={styles.viewBtn}>
          <Text style={styles.viewBtnText}>View Plan</Text>
          <Ionicons name="chevron-forward" size={13} color="#007AFF" />
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>My Trips</Text>
        <Text style={styles.headerSub}>{trips.length} trip{trips.length !== 1 ? 's' : ''} planned</Text>
      </View>

      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Loading your trips...</Text>
        </View>
      ) : trips.length === 0 ? (
        <View style={styles.centered}>
          <Ionicons name="map-outline" size={72} color="#ddd" />
          <Text style={styles.emptyTitle}>No trips yet</Text>
          <Text style={styles.emptyText}>Plan your first trip from the Plan tab!</Text>
        </View>
      ) : (
        <FlatList
          data={trips}
          keyExtractor={item => item.id.toString()}
          renderItem={renderTrip}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); fetchHistory(); }}
              tintColor="#007AFF"
            />
          }
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const cardShadow = Platform.select({
  web: { boxShadow: '0px 4px 10px rgba(0, 0, 0, 0.07)' } as any,
  default: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 4,
  },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fb' },
  header: {
    paddingTop: 54, paddingBottom: 14, paddingHorizontal: 20,
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f0f0f0',
  },
  headerTitle: { fontSize: 28, fontWeight: '800', color: '#1a1a2e' },
  headerSub: { color: '#888', fontSize: 14, marginTop: 2 },
  list: { padding: 16, gap: 14, paddingBottom: 32 },
  card: {
    backgroundColor: '#fff', borderRadius: 18, padding: 16,
    ...cardShadow,
  },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  cardMain: { flex: 1, marginRight: 8 },
  tripTitle: { fontSize: 17, fontWeight: '700', color: '#1a1a2e', marginBottom: 4 },
  routeRow: { flexDirection: 'row', alignItems: 'center' },
  routeText: { fontSize: 13, color: '#555', fontWeight: '500' },
  deleteBtn: { padding: 6, borderRadius: 8, backgroundColor: '#fff1f0' },
  metaRow: { flexDirection: 'row', gap: 16, marginBottom: 12 },
  metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  metaText: { fontSize: 12, color: '#888' },
  bottomRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  durationBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: '#eff6ff', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20,
  },
  durationText: { fontSize: 12, color: '#007AFF', fontWeight: '600' },
  budget: { fontSize: 14, fontWeight: '700', color: '#333' },
  viewBtn: { flexDirection: 'row', alignItems: 'center', gap: 2 },
  viewBtnText: { fontSize: 13, color: '#007AFF', fontWeight: '600' },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  loadingText: { color: '#888', fontSize: 14 },
  emptyTitle: { fontSize: 20, fontWeight: '700', color: '#ccc' },
  emptyText: { color: '#bbb', fontSize: 14 },
});
