import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  TextInput, ActivityIndicator, Image, RefreshControl, Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { ENDPOINTS } from '@/constants/config';
import api from '@/services/api';

const CATEGORIES = ['All', 'Nature', 'Culture', 'Temple', 'Beach', 'Adventure', 'Food', 'History', 'Wildlife'];

interface Destination {
  id: number;
  name: string;
  country: string;
  description: string;
  image_url: string | null;
  category: string;
  lat: number | null;
  lon: number | null;
  is_featured: boolean;
}

const FALLBACK_IMAGES: Record<string, string> = {
  Nature:    'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=600',
  Culture:   'https://images.unsplash.com/photo-1588258524675-c61d5e360e25?w=600',
  Temple:    'https://images.unsplash.com/photo-1605649487212-47bdab064df7?w=600',
  Beach:     'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=600',
  Adventure: 'https://images.unsplash.com/photo-1520520731457-9283dd14aa66?w=600',
  Food:      'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600',
  History:   'https://images.unsplash.com/photo-1599561046251-bfb9465b4c44?w=600',
  Wildlife:  'https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?w=600',
};

export default function ExploreScreen() {
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [filtered, setFiltered]         = useState<Destination[]>([]);
  const [loading, setLoading]           = useState(true);
  const [refreshing, setRefreshing]     = useState(false);
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [search, setSearch]             = useState('');

  const fetchDestinations = useCallback(async () => {
    try {
      const res = await api.get(ENDPOINTS.destinations);
      setDestinations(res.data);
      setFiltered(res.data);
    } catch (e) {
      console.error('Failed to load destinations:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchDestinations(); }, [fetchDestinations]);

  useEffect(() => {
    let result = destinations;
    if (selectedCategory !== 'All') {
      result = result.filter(d => d.category === selectedCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(d =>
        d.name.toLowerCase().includes(q) || d.description.toLowerCase().includes(q)
      );
    }
    setFiltered(result);
  }, [selectedCategory, search, destinations]);

  const getCategoryColor = (cat: string) => {
    const colors: Record<string, string> = {
      Nature: '#22c55e', Culture: '#a855f7', Temple: '#f97316',
      Beach: '#06b6d4', Adventure: '#ef4444', Food: '#eab308',
      History: '#8b5cf6', Wildlife: '#84cc16',
    };
    return colors[cat] || '#007AFF';
  };

  const renderItem = ({ item }: { item: Destination }) => {
    const imgUrl   = item.image_url || FALLBACK_IMAGES[item.category] || FALLBACK_IMAGES.Nature;
    const catColor = getCategoryColor(item.category);

    return (
      <View style={styles.card}>
        <Image source={{ uri: imgUrl }} style={styles.cardImage} resizeMode="cover" />
        <View style={styles.cardBody}>
          <View style={styles.cardTopRow}>
            <View style={[styles.categoryBadge, { backgroundColor: catColor + '22', borderColor: catColor }]}>
              <Text style={[styles.categoryText, { color: catColor }]}>{item.category}</Text>
            </View>
            {item.is_featured && (
              <View style={styles.featuredBadge}>
                <Ionicons name="star" size={10} color="#f59e0b" />
                <Text style={styles.featuredText}>Featured</Text>
              </View>
            )}
          </View>
          <Text style={styles.cardTitle}>{item.name}</Text>
          <View style={styles.locationRow}>
            <Ionicons name="location-outline" size={13} color="#888" />
            <Text style={styles.locationText}>{item.country}</Text>
          </View>
          <Text style={styles.cardDesc} numberOfLines={3}>{item.description}</Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Explore</Text>
        <Text style={styles.headerSub}>Discover amazing destinations</Text>
      </View>

      {/* Search */}
      <View style={styles.searchBar}>
        <Ionicons name="search" size={18} color="#999" style={{ marginRight: 8 }} />
        <TextInput
          style={styles.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="Search destinations..."
          placeholderTextColor="#bbb"
        />
        {search.length > 0 && (
          <TouchableOpacity onPress={() => setSearch('')}>
            <Ionicons name="close-circle" size={18} color="#ccc" />
          </TouchableOpacity>
        )}
      </View>

      {/* Category filter */}
      <FlatList
        data={CATEGORIES}
        keyExtractor={item => item}
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.categoryList}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.catChip, selectedCategory === item && styles.catChipSelected]}
            onPress={() => setSelectedCategory(item)}
          >
            <Text style={[styles.catChipText, selectedCategory === item && styles.catChipTextSelected]}>
              {item}
            </Text>
          </TouchableOpacity>
        )}
      />

      {/* Destinations list */}
      {loading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Loading destinations...</Text>
        </View>
      ) : filtered.length === 0 ? (
        <View style={styles.centered}>
          <Ionicons name="map-outline" size={60} color="#ddd" />
          <Text style={styles.emptyText}>No destinations found</Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={item => item.id.toString()}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); fetchDestinations(); }}
              tintColor="#007AFF"
            />
          }
          showsVerticalScrollIndicator={false}
        />
      )}
    </View>
  );
}

const searchShadow = Platform.select({
  web: { boxShadow: '0px 2px 6px rgba(0, 0, 0, 0.06)' } as any,
  default: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 3,
  },
});

const cardShadow = Platform.select({
  web: { boxShadow: '0px 4px 10px rgba(0, 0, 0, 0.08)' } as any,
  default: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 10,
    elevation: 5,
  },
});

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: '#f8f9fb' },
  header: {
    paddingTop: 54, paddingBottom: 14, paddingHorizontal: 20,
    backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#f0f0f0',
  },
  headerTitle: { fontSize: 28, fontWeight: '800', color: '#1a1a2e' },
  headerSub:   { color: '#888', fontSize: 14, marginTop: 2 },
  searchBar: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#fff', margin: 16, borderRadius: 14,
    paddingHorizontal: 14, height: 46,
    ...searchShadow,
  },
  searchInput:   { flex: 1, fontSize: 15, color: '#333' },
  categoryList:  { paddingHorizontal: 16, paddingBottom: 12, gap: 8 },
  catChip: {
    paddingHorizontal: 18, paddingVertical: 7, borderRadius: 20,
    backgroundColor: '#f0f0f0', borderWidth: 1, borderColor: '#e5e5e5',
  },
  catChipSelected:     { backgroundColor: '#007AFF', borderColor: '#007AFF' },
  catChipText:         { color: '#555', fontWeight: '600', fontSize: 13 },
  catChipTextSelected: { color: '#fff' },
  list: { padding: 16, gap: 16, paddingBottom: 32 },
  card: {
    backgroundColor: '#fff', borderRadius: 18, overflow: 'hidden',
    ...cardShadow,
  },
  cardImage:  { width: '100%', height: 180 },
  cardBody:   { padding: 16 },
  cardTopRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 8 },
  categoryBadge: { paddingHorizontal: 10, paddingVertical: 3, borderRadius: 20, borderWidth: 1 },
  categoryText:  { fontSize: 11, fontWeight: '700' },
  featuredBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 3,
    backgroundColor: '#fef9c3', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 20,
  },
  featuredText: { fontSize: 11, fontWeight: '700', color: '#b45309' },
  cardTitle:    { fontSize: 18, fontWeight: '700', color: '#1a1a2e', marginBottom: 4 },
  locationRow:  { flexDirection: 'row', alignItems: 'center', gap: 3, marginBottom: 8 },
  locationText: { fontSize: 12, color: '#888' },
  cardDesc:     { fontSize: 13, color: '#666', lineHeight: 19 },
  centered:     { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 10 },
  loadingText:  { color: '#888', fontSize: 14 },
  emptyText:    { color: '#bbb', fontSize: 16, fontWeight: '500' },
});
