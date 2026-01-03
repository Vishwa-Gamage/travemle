import React, { useState } from 'react';
import { StyleSheet, Text, View, TextInput, TouchableOpacity, ScrollView, ImageBackground } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import axios from 'axios';
import DateTimePickerModal from "react-native-modal-datetime-picker";

export default function HomeScreen() {
  const router = useRouter();
  const [city, setCity] = useState('Kandy');
  const [budget, setBudget] = useState('50000');
  const [selectedInterests, setSelectedInterests] = useState<string[]>(['Culture', 'Temple']);
  const [selectedMode, setSelectedMode] = useState('Bus');
  const [loading, setLoading] = useState(false);

  // Date States
  const [startDate, setStartDate] = useState(new Date());
  const [endDate, setEndDate] = useState(new Date(new Date().setDate(new Date().getDate() + 3))); // Default 3 days later
  const [isStartPickerVisible, setStartPickerVisibility] = useState(false);
  const [isEndPickerVisible, setEndPickerVisibility] = useState(false);

  const interests = ['Nature', 'Culture', 'Temple', 'Beach', 'Adventure', 'Food'];

  // --- Date Picker Logic ---
  const showStartPicker = () => setStartPickerVisibility(true);
  const hideStartPicker = () => setStartPickerVisibility(false);
  const handleConfirmStart = (date: Date) => {
    setStartDate(date);
    hideStartPicker();
  };

  const showEndPicker = () => setEndPickerVisibility(true);
  const hideEndPicker = () => setEndPickerVisibility(false);
  const handleConfirmEnd = (date: Date) => {
    setEndDate(date);
    hideEndPicker();
  };

  const formatDate = (date: Date) => {
    return date.toISOString().split('T')[0]; // Returns YYYY-MM-DD
  };
  // -------------------------

  const toggleInterest = (interest: string) => {
    if (selectedInterests.includes(interest)) {
      setSelectedInterests(selectedInterests.filter(i => i !== interest));
    } else {
      setSelectedInterests([...selectedInterests, interest]);
    }
  };

  const handlePlanTrip = async () => {
    setLoading(true);
    try {
      // ඔයාගේ IP එක මෙතන දැම්මා
      const response = await axios.post('http://192.168.52.16:8000/api/plan-trip/', {
        origin: 'Colombo',
        city: city,
        country: 'Sri Lanka',
        start_date: formatDate(startDate),
        end_date: formatDate(endDate),
        interests: selectedInterests.join(', '),
        budget: parseInt(budget),
        travel_mode: selectedMode
      });

      const planData = response.data;
      
      router.push({
        pathname: "/result",
        params: { 
          data: JSON.stringify(planData.plan),
          weather: planData.weather,
          map_url: planData.map_url
        }
      });

    } catch (error) {
      console.error(error);
      alert("Error connecting to server. Check if backend is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.logoRow}>
          <Ionicons name="location-sharp" size={24} color="#007AFF" />
          <Text style={styles.logoText}>Travemle</Text>
        </View>
        <Text style={styles.subtitle}>Plan your dream journey</Text>
      </View>

      <ImageBackground 
        source={{ uri: 'https://images.unsplash.com/photo-1588258524675-c61d5e360e25?q=80&w=1000&auto=format&fit=crop' }} 
        style={styles.backgroundImage}
        imageStyle={{ opacity: 0.4 }} 
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          
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

          {/* --- Updated Date Pickers --- */}
          <View style={styles.row}>
            <View style={{ flex: 1, marginRight: 10 }}>
              <Text style={styles.label}>Start Date</Text>
              <TouchableOpacity style={styles.inputContainer} onPress={showStartPicker}>
                <Ionicons name="calendar-outline" size={20} color="#666" style={styles.icon} />
                <Text style={styles.dateText}>{formatDate(startDate)}</Text>
              </TouchableOpacity>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.label}>End Date</Text>
              <TouchableOpacity style={styles.inputContainer} onPress={showEndPicker}>
                <Ionicons name="calendar-outline" size={20} color="#666" style={styles.icon} />
                <Text style={styles.dateText}>{formatDate(endDate)}</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Calendar Modals */}
          <DateTimePickerModal
            isVisible={isStartPickerVisible}
            mode="date"
            onConfirm={handleConfirmStart}
            onCancel={hideStartPicker}
          />
          <DateTimePickerModal
            isVisible={isEndPickerVisible}
            mode="date"
            onConfirm={handleConfirmEnd}
            onCancel={hideEndPicker}
            minimumDate={startDate} 
          />
          {/* ------------------------- */}

          <Text style={styles.label}>Budget (LKR)</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="wallet-outline" size={20} color="#666" style={styles.icon} />
            <TextInput 
              style={styles.input} 
              value={budget}
              onChangeText={setBudget}
              keyboardType="numeric"
            />
          </View>

          <Text style={styles.label}>Interests</Text>
          <View style={styles.chipsContainer}>
            {interests.map((item) => {
              const isSelected = selectedInterests.includes(item);
              return (
                <TouchableOpacity 
                  key={item} 
                  style={[styles.chip, isSelected && styles.chipSelected]}
                  onPress={() => toggleInterest(item)}
                >
                  <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>
                    {item}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>

          <Text style={styles.label}>Travel Mode</Text>
          <View style={styles.modesContainer}>
            {['Car', 'Bus', 'Train'].map((mode) => {
              const isSelected = selectedMode === mode;
              return (
                <TouchableOpacity 
                  key={mode} 
                  style={[styles.modeButton, isSelected && styles.modeButtonSelected]}
                  onPress={() => setSelectedMode(mode)}
                >
                  <Ionicons 
                    name={mode === 'Car' ? 'car-sport-outline' : mode === 'Bus' ? 'bus-outline' : 'train-outline'} 
                    size={28} 
                    color={isSelected ? "#007AFF" : "#666"} 
                  />
                  <Text style={[styles.modeText, isSelected && styles.modeTextSelected]}>{mode}</Text>
                </TouchableOpacity>
              );
            })}
          </View>

        </ScrollView>

        <View style={styles.footer}>
          <TouchableOpacity style={styles.planButton} onPress={handlePlanTrip} disabled={loading}>
            <Text style={styles.planButtonText}>{loading ? "Planning..." : "Plan My Trip"}</Text>
          </TouchableOpacity>
        </View>

      </ImageBackground>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  header: { paddingTop: 50, paddingBottom: 20, paddingHorizontal: 20, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f0f0f0', zIndex: 10 },
  logoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 5 },
  logoText: { fontSize: 24, fontWeight: 'bold', color: '#007AFF', marginLeft: 5 },
  subtitle: { color: '#666', fontSize: 14 },
  backgroundImage: { flex: 1, resizeMode: 'cover' },
  scrollContent: { padding: 20, paddingBottom: 100 },
  label: { fontSize: 14, color: '#333', fontWeight: '600', marginBottom: 8, marginTop: 15 },
  inputContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 12, borderWidth: 1, borderColor: '#007AFF', paddingHorizontal: 15, height: 50 },
  input: { flex: 1, fontSize: 16, color: '#000' },
  icon: { marginRight: 10 },
  row: { flexDirection: 'row', justifyContent: 'space-between' },
  dateText: { fontSize: 16, color: '#000' },
  chipsContainer: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  chip: { paddingVertical: 8, paddingHorizontal: 20, borderRadius: 25, backgroundColor: '#f5f5f5', borderWidth: 1, borderColor: '#e0e0e0' },
  chipSelected: { backgroundColor: '#007AFF', borderColor: '#007AFF' },
  chipText: { color: '#333', fontWeight: '500' },
  chipTextSelected: { color: '#fff' },
  modesContainer: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10 },
  modeButton: { width: '30%', backgroundColor: '#fff', padding: 15, borderRadius: 12, alignItems: 'center', borderWidth: 1, borderColor: '#ddd', shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  modeButtonSelected: { borderColor: '#007AFF', backgroundColor: '#eff6ff', borderWidth: 2 },
  modeText: { marginTop: 5, fontSize: 12, color: '#666', fontWeight: '600' },
  modeTextSelected: { color: '#007AFF' },
  footer: { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: '#fff', padding: 20, borderTopWidth: 1, borderTopColor: '#eee' },
  planButton: { backgroundColor: '#007AFF', paddingVertical: 16, borderRadius: 12, alignItems: 'center' },
  planButtonText: { color: '#fff', fontSize: 18, fontWeight: 'bold' },
});