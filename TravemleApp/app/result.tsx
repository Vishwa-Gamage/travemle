import React from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, Linking, Alert, Platform } from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

type LocalSearchParams = {
  data: string;
  weather: string;
  map_url: string;
};

export default function ResultScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<LocalSearchParams>();

  const plan = params.data ? JSON.parse(params.data) : null;
  const weather = params.weather || '';
  const mapUrl = params.map_url || '';

  if (!plan) {
    return (
      <View style={styles.errorContainer}>
        <Ionicons name="alert-circle-outline" size={60} color="#ff3b30" />
        <Text style={styles.errorTitle}>Plan Not Found</Text>
        <Text style={styles.errorSub}>Something went wrong loading your plan.</Text>
        <TouchableOpacity style={styles.backBtnLarge} onPress={() => router.back()}>
          <Text style={styles.backBtnText}>Go Back</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const openMap = () => {
    if (mapUrl) {
      Linking.openURL(mapUrl).catch(() =>
        Alert.alert('Error', 'Could not open Google Maps.')
      );
    }
  };

  // Robustly parse weather string
  const displayWeather = () => {
    if (!weather || weather.length < 2) return 'Unavailable';
    // Format: "Description, temp°C, Humidity X%, Rain Y%"
    // Return temp part for compact badge
    const parts = weather.split(',');
    return parts.length >= 2 ? parts[1].trim() : weather;
  };

  const fullWeather = () => weather || 'Weather unavailable';

  // --- STRONG CALCULATION FIX FOR MOBILE ---
  const calculateTotal = () => {
    // 1. If no budget data, return 0
    if (!plan.budget_breakdown) return "0.00";
    
    let total = 0;
    
    Object.entries(plan.budget_breakdown).forEach(([key, value]) => {
      // Skip the existing 'total' key to avoid double counting
      if (key !== 'total') {
        // 2. Convert value to String first (safeguard)
        let stringValue = String(value);
        
        // 3. Remove everything except numbers and dots (e.g., "5,000" -> "5000", "LKR 200" -> "200")
        let cleanString = stringValue.replace(/[^0-9.]/g, '');
        
        // 4. Parse to float
        const amount = parseFloat(cleanString);
        
        // 5. Add if it is a valid number
        if (!isNaN(amount)) {
          total += amount;
        }
      }
    });
    
    // 6. Return formatted total (2 decimal places)
    return total.toFixed(2);
  };
  // -----------------------------------------

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Your Trip Plan</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>

        {/* 1. Trip Summary Card */}
        <View style={styles.summaryCard}>
          <View style={styles.summaryLeft}>
            <Text style={styles.tripTitle}>{plan.title}</Text>
            <View style={styles.durationRow}>
              <Ionicons name="calendar-outline" size={14} color="#888" />
              <Text style={styles.duration}>{plan.duration}</Text>
            </View>
          </View>
          <View style={styles.weatherBadge}>
            <Ionicons name="partly-sunny" size={26} color="#FFD700" />
            <Text style={styles.weatherTemp}>{displayWeather()}</Text>
          </View>
        </View>

        {/* Weather details */}
        {weather.length > 2 && (
          <View style={styles.weatherDetail}>
            <Ionicons name="cloud-outline" size={16} color="#007AFF" />
            <Text style={styles.weatherDetailText}>{fullWeather()}</Text>
          </View>
        )}

        {/* 2. Map Button */}
        <TouchableOpacity style={styles.mapButton} onPress={openMap}>
          <Ionicons name="map" size={20} color="#fff" style={{ marginRight: 8 }} />
          <Text style={styles.mapButtonText}>View Route on Google Maps</Text>
        </TouchableOpacity>

        {/* 3. Itinerary */}
        <Text style={styles.sectionTitle}>Daily Itinerary</Text>

        {(plan.activities || []).map((activity: any, index: number) => (
          <View key={index} style={styles.activityCard}>
            <View style={styles.timeColumn}>
              <Text style={styles.timeText}>{activity.time}</Text>
              {index < plan.activities.length - 1 && <View style={styles.line} />}
            </View>
            <View style={styles.detailsColumn}>
              <Text style={styles.locationName}>{activity.location_name}</Text>
              <Text style={styles.description}>{activity.description}</Text>
              <View style={styles.dayBadge}>
                <Text style={styles.dayBadgeText}>{activity.day}</Text>
              </View>
            </View>
          </View>
        ))}

        {/* 4. Budget Breakdown */}
        {plan.budget_breakdown && (
          <View style={styles.budgetCard}>
            <Text style={styles.budgetTitle}>💰 Budget Breakdown</Text>
            <View style={styles.breakdownContainer}>
              {Object.entries(plan.budget_breakdown).map(([key, value]) => {
                if (key === 'total') return null;
                return (
                  <View key={key} style={styles.budgetRow}>
                    <Text style={styles.budgetItem}>
                      {key.charAt(0).toUpperCase() + key.slice(1)}
                    </Text>
                    <Text style={styles.budgetCost}>{String(value)} LKR</Text>
                  </View>
                );
              })}
            </View>
            <View style={styles.divider} />
            <View style={styles.totalRow}>
              <Text style={styles.budgetLabel}>Total Estimated Cost</Text>
              <Text style={styles.budgetAmount}>LKR {calculateTotal()}</Text>
            </View>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  errorContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32, gap: 12 },
  errorTitle: { fontSize: 22, fontWeight: '700', color: '#333' },
  errorSub: { fontSize: 14, color: '#888', textAlign: 'center' },
  backBtnLarge: {
    marginTop: 12, backgroundColor: '#007AFF', paddingVertical: 12,
    paddingHorizontal: 28, borderRadius: 12,
  },
  backBtnText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  header: {
    paddingTop: 52, paddingBottom: 14, paddingHorizontal: 16,
    backgroundColor: '#fff', flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between', borderBottomWidth: 1, borderBottomColor: '#eee',
  },
  backButton: { padding: 6 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#1a1a2e' },
  scrollContent: { padding: 18, paddingBottom: 60 },
  summaryCard: {
    backgroundColor: '#fff', borderRadius: 18, padding: 18,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start',
    marginBottom: 10, elevation: 3,
    ...Platform.select({
      web: { boxShadow: '0px 3px 8px rgba(0, 0, 0, 0.08)' } as any,
      default: { shadowColor: '#000', shadowOffset: { width: 0, height: 3 }, shadowOpacity: 0.08, shadowRadius: 8 },
    }),
  },
  summaryLeft: { flex: 1, marginRight: 10 },
  tripTitle: { fontSize: 19, fontWeight: '800', color: '#007AFF', marginBottom: 6, flexWrap: 'wrap' },
  durationRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  duration: { color: '#888', fontSize: 13 },
  weatherBadge: { alignItems: 'center', backgroundColor: '#fffbe6', padding: 12, borderRadius: 14 },
  weatherTemp: { fontWeight: '700', marginTop: 4, fontSize: 12, color: '#333' },
  weatherDetail: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: '#eff6ff', borderRadius: 10, paddingHorizontal: 14, paddingVertical: 8,
    marginBottom: 14,
  },
  weatherDetailText: { color: '#555', fontSize: 13, flex: 1 },
  mapButton: {
    backgroundColor: '#34C759', padding: 15, borderRadius: 14,
    flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginBottom: 22,
    elevation: 2,
  },
  mapButtonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  sectionTitle: { fontSize: 19, fontWeight: '800', marginBottom: 14, color: '#1a1a2e' },
  activityCard: { flexDirection: 'row', marginBottom: 16 },
  timeColumn: { alignItems: 'center', marginRight: 14, width: 52 },
  timeText: { fontWeight: '700', color: '#007AFF', fontSize: 12, textAlign: 'center' },
  line: { width: 2, flex: 1, backgroundColor: '#ddd', marginTop: 6 },
  detailsColumn: {
    flex: 1, backgroundColor: '#fff', padding: 14, borderRadius: 14, elevation: 1,
    ...Platform.select({
      web: { boxShadow: '0px 2px 6px rgba(0, 0, 0, 0.05)' } as any,
      default: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.05, shadowRadius: 6 },
    }),
  },
  locationName: { fontSize: 15, fontWeight: '700', marginBottom: 4, color: '#1a1a2e' },
  description: { color: '#666', fontSize: 13, lineHeight: 19 },
  dayBadge: {
    marginTop: 8, alignSelf: 'flex-start',
    backgroundColor: '#f0f4ff', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6,
  },
  dayBadgeText: { fontSize: 11, color: '#007AFF', fontWeight: '600' },
  budgetCard: {
    backgroundColor: '#1a1a2e', padding: 20, borderRadius: 18, marginTop: 10,
    elevation: 6,
    ...Platform.select({
      web: { boxShadow: '0px 4px 10px rgba(0, 0, 0, 0.20)' } as any,
      default: { shadowColor: '#000', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.2, shadowRadius: 10 },
    }),
  },
  budgetTitle: { color: '#fff', fontSize: 18, fontWeight: '800', marginBottom: 16 },
  breakdownContainer: { gap: 8 },
  budgetRow: { flexDirection: 'row', justifyContent: 'space-between' },
  budgetItem: { color: '#aaa', fontSize: 14 },
  budgetCost: { color: '#fff', fontWeight: '600', fontSize: 14 },
  divider: { height: 1, backgroundColor: '#333', marginVertical: 14 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  budgetLabel: { color: '#aaa', fontSize: 14 },
  budgetAmount: { color: '#4ade80', fontSize: 24, fontWeight: '800' },
});