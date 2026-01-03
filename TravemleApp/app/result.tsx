import React from 'react';
import { StyleSheet, Text, View, ScrollView, TouchableOpacity, Linking } from 'react-native';
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
  const weather = params.weather;
  const mapUrl = params.map_url;

  if (!plan) {
    return (
      <View style={styles.container}>
        <Text style={{textAlign: 'center', marginTop: 50}}>Loading Plan...</Text>
      </View>
    );
  }

  const openMap = () => {
    if (mapUrl) {
      Linking.openURL(mapUrl);
    }
  };

  // Weather Logic: හරියට Comma තියෙනවද බලලා Split කරනවා, නැත්නම් නිකන්ම පෙන්නනවා
  const displayWeather = () => {
    if (!weather) return "Unavailable";
    if (weather.includes(',')) {
      return weather.split(',')[1]; // උදා: "Clouds, 28°C" -> "28°C"
    }
    return weather; // Error එකක් නම් කෙලින්ම පෙන්නනවා
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Your Trip Plan</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        
        {/* 1. Trip Summary Card */}
        <View style={styles.summaryCard}>
          <View>
            <Text style={styles.tripTitle}>{plan.title}</Text>
            <Text style={styles.duration}>🗓 {plan.duration}</Text>
          </View>
          <View style={styles.weatherBadge}>
            <Ionicons name="partly-sunny" size={24} color="#FFD700" />
            <Text style={styles.weatherText}>{displayWeather()}</Text>
          </View>
        </View>

        {/* 2. Map Button */}
        <TouchableOpacity style={styles.mapButton} onPress={openMap}>
          <Ionicons name="map" size={20} color="#fff" style={{marginRight:8}} />
          <Text style={styles.mapButtonText}>View Route on Google Maps</Text>
        </TouchableOpacity>

        {/* 3. Itinerary List */}
        <Text style={styles.sectionTitle}>Daily Itinerary</Text>
        
        {plan.activities.map((activity: any, index: number) => (
          <View key={index} style={styles.activityCard}>
            <View style={styles.timeColumn}>
              <Text style={styles.timeText}>{activity.time}</Text>
              <View style={styles.line} />
            </View>
            <View style={styles.detailsColumn}>
              <Text style={styles.locationName}>{activity.location_name}</Text>
              <Text style={styles.description}>{activity.description}</Text>
              <Text style={styles.dayTag}>{activity.day}</Text>
            </View>
          </View>
        ))}

        {/* 4. Budget Breakdown (FIXED) */}
        <View style={styles.budgetCard}>
          <Text style={styles.budgetTitle}>💰 Budget Breakdown</Text>
          
          {/* Loop through budget items */}
          <View style={styles.breakdownContainer}>
            {plan.budget_breakdown && Object.entries(plan.budget_breakdown).map(([key, value]) => {
              if (key === 'total') return null; // Total එක වෙනම පෙන්නන නිසා මෙතනින් අයින් කරනවා
              return (
                <View key={key} style={styles.budgetRow}>
                  <Text style={styles.budgetItem}>{key.charAt(0).toUpperCase() + key.slice(1)}</Text>
                  <Text style={styles.budgetCost}>{value} LKR</Text>
                </View>
              );
            })}
          </View>

          <View style={styles.divider} />
          
          <Text style={styles.budgetLabel}>Total Estimated Cost</Text>
          <Text style={styles.budgetAmount}>LKR {plan.budget_breakdown?.total}</Text>
        </View>

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8f9fa' },
  header: { paddingTop: 50, paddingBottom: 15, paddingHorizontal: 20, backgroundColor: '#fff', flexDirection: 'row', alignItems: 'center', borderBottomWidth: 1, borderBottomColor: '#eee' },
  backButton: { marginRight: 15 },
  headerTitle: { fontSize: 18, fontWeight: 'bold' },
  scrollContent: { padding: 20, paddingBottom: 50 },
  summaryCard: { backgroundColor: '#fff', borderRadius: 16, padding: 20, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15, elevation: 2 },
  tripTitle: { fontSize: 20, fontWeight: 'bold', color: '#007AFF', maxWidth: 200 },
  duration: { color: '#666', marginTop: 5 },
  weatherBadge: { alignItems: 'center', backgroundColor: '#fffbe6', padding: 10, borderRadius: 12 },
  weatherText: { fontWeight: 'bold', marginTop: 4, fontSize: 12 },
  mapButton: { backgroundColor: '#34C759', padding: 15, borderRadius: 12, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginBottom: 25 },
  mapButtonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
  sectionTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 15, color: '#333' },
  activityCard: { flexDirection: 'row', marginBottom: 20 },
  timeColumn: { alignItems: 'center', marginRight: 15, width: 50 },
  timeText: { fontWeight: 'bold', color: '#007AFF' },
  line: { width: 2, flex: 1, backgroundColor: '#ddd', marginTop: 5 },
  detailsColumn: { flex: 1, backgroundColor: '#fff', padding: 15, borderRadius: 12, elevation: 1 },
  locationName: { fontSize: 16, fontWeight: 'bold', marginBottom: 4 },
  description: { color: '#666', fontSize: 13, lineHeight: 18 },
  dayTag: { position: 'absolute', top: 10, right: 10, fontSize: 10, backgroundColor: '#eee', padding: 4, borderRadius: 4 },
  
  // Budget Styles
  budgetCard: { backgroundColor: '#333', padding: 20, borderRadius: 16, marginTop: 10 },
  budgetTitle: { color: '#fff', fontSize: 18, fontWeight: 'bold', marginBottom: 15, textAlign: 'center' },
  breakdownContainer: { marginBottom: 10 },
  budgetRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  budgetItem: { color: '#ccc', fontSize: 14 },
  budgetCost: { color: '#fff', fontWeight: '600' },
  divider: { height: 1, backgroundColor: '#555', marginVertical: 10 },
  budgetLabel: { color: '#aaa', fontSize: 14, textAlign: 'center' },
  budgetAmount: { color: '#4ade80', fontSize: 28, fontWeight: 'bold', marginTop: 5, textAlign: 'center' }
});