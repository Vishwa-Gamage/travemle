import React, { useState, useEffect } from 'react';
import {
  StyleSheet, Text, View, TextInput, TouchableOpacity, ScrollView,
  ActivityIndicator, Modal, ImageBackground, Alert, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import DateTimePickerModal from 'react-native-modal-datetime-picker';

import { useAuth } from '@/context/AuthContext';
import { ENDPOINTS } from '@/constants/config';
import api from '@/services/api';

const INTERESTS = ['Nature', 'Culture', 'Temple', 'Beach', 'Adventure', 'Food'];
const TRAVEL_MODES = ['Car', 'Bus', 'Train'] as const;

export default function HomeScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const [origin, setOrigin]   = useState('Colombo');
  const [country, setCountry] = useState('Sri Lanka');
  const [city, setCity]       = useState('');
  const [budget, setBudget]   = useState('50000');
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['Culture', 'Temple']);
  const [selectedMode, setSelectedMode]           = useState<string>('Bus');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.profile) {
      setBudget(user.profile.default_budget.toString());
      setSelectedMode(user.profile.default_travel_mode);
      if (user.profile.interests_csv) {
        setSelectedInterests(user.profile.interests_csv.split(',').map((s: string) => s.trim()));
      }
    }
  }, [user]);

  const [startDate, setStartDate]               = useState(new Date());
  const [endDate, setEndDate]                   = useState(new Date(Date.now() + 3 * 86400000));
  const [isStartPickerVisible, setStartPickerVisible] = useState(false);
  const [isEndPickerVisible, setEndPickerVisible]     = useState(false);

  const formatDate = (d: Date) => d.toISOString().split('T')[0];

  const handleConfirmStart = (date: Date) => {
    setStartDate(date);
    if (date >= endDate) {
      setEndDate(new Date(date.getTime() + 86400000));
    }
    setStartPickerVisible(false);
  };

  const handleConfirmEnd = (date: Date) => {
    setEndDate(date);
    setEndPickerVisible(false);
  };

  const toggleInterest = (interest: string) => {
    setSelectedInterests(prev =>
      prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]
    );
  };

  const handlePlanTrip = async () => {
    if (!city.trim()) {
      Alert.alert('Missing Destination', 'Please enter a destination city.');
      return;
    }
    if (endDate <= startDate) {
      Alert.alert('Invalid Dates', 'End date must be after start date.');
      return;
    }

    setLoading(true);
    try {
      // api.ts automatically attaches the Bearer token
      const response = await api.post(ENDPOINTS.planTrip, {
        origin:      origin.trim() || 'Colombo',
        city:        city.trim(),
        country:     country.trim() || 'Sri Lanka',
        start_date:  formatDate(startDate),
        end_date:    formatDate(endDate),
        interests:   selectedInterests.join(', '),
        budget:      parseInt(budget) || 20000,
        travel_mode: selectedMode,
      });

      const planData = response.data;
      router.push({
        pathname: '/result',
        params: {
          data:    JSON.stringify(planData.plan),
          weather: planData.weather,
          map_url: planData.map_url,
        },
      });
    } catch (err: any) {
      const msg =
        err?.response?.data?.error ||
        'Could not connect to server. Is the backend running?';
      Alert.alert('Error', msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <Ionicons name="location-sharp" size={24} color="#007AFF" />
          <Text style={styles.logoText}>Travemle</Text>
        </View>
        <View style={styles.userRow}>
          <Text style={styles.userGreeting}>Hi, {user?.username}</Text>
          <TouchableOpacity onPress={logout}>
            <Ionicons name="log-out-outline" size={22} color="#ff3b30" />
          </TouchableOpacity>
        </View>
      </View>

      <ImageBackground
        source={{ uri: 'https://images.unsplash.com/photo-1588258524675-c61d5e360e25?q=80&w=1000' }}
        style={styles.backgroundImage}
        imageStyle={{ opacity: 0.3 }}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>

          {/* Origin */}
          <Text style={styles.label}>Starting Point</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="navigate-outline" size={20} color="#666" style={styles.icon} />
            <TextInput
              style={styles.input}
              value={origin}
              onChangeText={setOrigin}
              placeholder="e.g. Colombo"
            />
          </View>

          {/* Country */}
          <Text style={styles.label}>Country</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="globe-outline" size={20} color="#666" style={styles.icon} />
            <TextInput
              style={styles.input}
              value={country}
              onChangeText={setCountry}
              placeholder="e.g. Sri Lanka"
            />
          </View>

          {/* Destination City */}
          <Text style={styles.label}>Destination City</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="search" size={20} color="#666" style={styles.icon} />
            <TextInput
              style={styles.input}
              value={city}
              onChangeText={setCity}
              placeholder="Where do you want to go?"
            />
          </View>

          {/* Date Pickers */}
          <View style={styles.row}>
            <View style={{ flex: 1, marginRight: 10 }}>
              <Text style={styles.label}>Start Date</Text>
              {Platform.OS === 'web' ? (
                <div style={styles.inputContainer as any}>
                  <Ionicons name="calendar-outline" size={20} color="#666" style={styles.icon as any} />
                  <input
                    type="date"
                    style={{ flex: 1, border: 'none', outline: 'none', fontSize: 15, background: 'transparent' }}
                    value={formatDate(startDate)}
                    onChange={(e) => handleConfirmStart(new Date(e.target.value))}
                    min={formatDate(new Date())}
                  />
                </div>
              ) : (
                <TouchableOpacity style={styles.inputContainer} onPress={() => setStartPickerVisible(true)}>
                  <Ionicons name="calendar-outline" size={20} color="#666" style={styles.icon} />
                  <Text style={styles.dateText}>{formatDate(startDate)}</Text>
                </TouchableOpacity>
              )}
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>End Date</Text>
              {Platform.OS === 'web' ? (
                <div style={styles.inputContainer as any}>
                  <Ionicons name="calendar-outline" size={20} color="#666" style={styles.icon as any} />
                  <input
                    type="date"
                    style={{ flex: 1, border: 'none', outline: 'none', fontSize: 15, background: 'transparent' }}
                    value={formatDate(endDate)}
                    onChange={(e) => handleConfirmEnd(new Date(e.target.value))}
                    min={formatDate(new Date(startDate.getTime() + 86400000))}
                  />
                </div>
              ) : (
                <TouchableOpacity style={styles.inputContainer} onPress={() => setEndPickerVisible(true)}>
                  <Ionicons name="calendar-outline" size={20} color="#666" style={styles.icon} />
                  <Text style={styles.dateText}>{formatDate(endDate)}</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>

          {Platform.OS !== 'web' && (
            <>
              <DateTimePickerModal
                isVisible={isStartPickerVisible}
                mode="date"
                onConfirm={handleConfirmStart}
                onCancel={() => setStartPickerVisible(false)}
                minimumDate={new Date()}
              />
              <DateTimePickerModal
                isVisible={isEndPickerVisible}
                mode="date"
                onConfirm={handleConfirmEnd}
                onCancel={() => setEndPickerVisible(false)}
                minimumDate={new Date(startDate.getTime() + 86400000)}
              />
            </>
          )}

          {/* Budget */}
          <Text style={styles.label}>Budget (LKR)</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="wallet-outline" size={20} color="#666" style={styles.icon} />
            <TextInput
              style={styles.input}
              value={budget}
              onChangeText={setBudget}
              keyboardType="numeric"
              placeholder="20000"
            />
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

          {/* Travel Mode */}
          <Text style={styles.label}>Travel Mode</Text>
          <View style={styles.modesContainer}>
            {TRAVEL_MODES.map((mode) => {
              const sel  = selectedMode === mode;
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

        </ScrollView>

        {/* Footer CTA */}
        <View style={styles.footer}>
          <TouchableOpacity
            style={[styles.planButton, loading && styles.planButtonDisabled]}
            onPress={handlePlanTrip}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" size="small" />
              : <Text style={styles.planButtonText}>Plan My Trip</Text>
            }
          </TouchableOpacity>
        </View>
      </ImageBackground>

      {/* Full-screen loading overlay */}
      <Modal transparent visible={loading} animationType="fade">
        <View style={styles.overlay}>
          <View style={styles.overlayCard}>
            <ActivityIndicator size="large" color="#007AFF" />
            <Text style={styles.overlayText}>AI is planning your trip...</Text>
            <Text style={styles.overlaySub}>This may take 10-20 seconds</Text>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const modeButtonShadow = Platform.select({
  web: { boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.08)' } as any,
  default: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
  },
});

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: {
    paddingTop: 52, paddingBottom: 14, paddingHorizontal: 20,
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f0f0f0',
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  logoRow:      { flexDirection: 'row', alignItems: 'center' },
  logoText:     { fontSize: 22, fontWeight: '800', color: '#007AFF', marginLeft: 6 },
  userRow:      { flexDirection: 'row', alignItems: 'center', gap: 10 },
  userGreeting: { color: '#555', fontSize: 13, fontWeight: '500' },
  backgroundImage:  { flex: 1, resizeMode: 'cover' },
  scrollContent:    { padding: 20, paddingBottom: 110 },
  label: { fontSize: 13, color: '#333', fontWeight: '600', marginBottom: 8, marginTop: 16 },
  inputContainer: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff',
    borderRadius: 12, borderWidth: 1.5, borderColor: '#007AFF',
    paddingHorizontal: 14, height: 50,
  },
  input:    { flex: 1, fontSize: 16, color: '#000' },
  icon:     { marginRight: 10 },
  row:      { flexDirection: 'row' },
  dateText: { fontSize: 15, color: '#000' },
  chipsContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chip: {
    paddingVertical: 8, paddingHorizontal: 20, borderRadius: 25,
    backgroundColor: '#f5f5f5', borderWidth: 1, borderColor: '#e0e0e0',
  },
  chipSelected:     { backgroundColor: '#007AFF', borderColor: '#007AFF' },
  chipText:         { color: '#333', fontWeight: '500' },
  chipTextSelected: { color: '#fff' },
  modesContainer: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  modeButton: {
    width: '30%', backgroundColor: '#fff', padding: 15, borderRadius: 12,
    alignItems: 'center', borderWidth: 1, borderColor: '#ddd',
    ...modeButtonShadow,
  },
  modeButtonSelected: { borderColor: '#007AFF', backgroundColor: '#eff6ff', borderWidth: 2 },
  modeText:         { marginTop: 5, fontSize: 12, color: '#666', fontWeight: '600' },
  modeTextSelected: { color: '#007AFF' },
  footer: {
    position: 'absolute', bottom: 0, left: 0, right: 0,
    backgroundColor: '#fff', padding: 16, borderTopWidth: 1, borderTopColor: '#eee',
  },
  planButton: {
    backgroundColor: '#007AFF', paddingVertical: 15,
    borderRadius: 14, alignItems: 'center', elevation: 3,
  },
  planButtonDisabled: { opacity: 0.6 },
  planButtonText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center' },
  overlayCard: {
    backgroundColor: '#fff', borderRadius: 20, padding: 36,
    alignItems: 'center', width: 260,
  },
  overlayText: { marginTop: 16, fontSize: 16, fontWeight: '600', color: '#333' },
  overlaySub:  { marginTop: 6, fontSize: 12, color: '#888' },
});