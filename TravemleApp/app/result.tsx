import React from 'react';
import {
  StyleSheet, Text, View, ScrollView, TouchableOpacity,
  Linking, Alert, Platform,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

// ── Types ────────────────────────────────────────────────────────────────────
type LocalSearchParams = {
  data:         string;
  weather:      string;
  map_url:      string;
  weather_days: string;   // JSON array of per-day forecast objects
  season_info:  string;
  budget_ref:   string;
  alternatives: string;
};

interface WeatherDay {
  date:        string;
  day_label:   string;
  day_num:     string;
  description: string;
  emoji:       string;
  temp:        number | null;
  temp_min:    number | null;
  temp_max:    number | null;
  humidity:    number | null;
  rain_pct:    number | null;
  available:   boolean;
}

interface SeasonInfo {
  season:       string;   // 'peak' | 'shoulder' | 'off_peak' | 'unknown'
  label:        string;
  icon:         string;
  region:       string;
  price_impact: string;
  month:        string;
  tip:          string;
  source:       string;
}

interface BudgetRefItem {
  category:     string;
  market_range: string;
  source:       string;
}

interface BudgetRef {
  tier:              string;
  tier_label:        string;
  per_day_estimated: number;
  references:        BudgetRefItem[];
  validation_note:   string;
}

interface Alternative {
  name:        string;
  category:    string;
  description: string;
  reason:      string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const safeParseJson = <T,>(str: string | undefined, fallback: T): T => {
  try { return str ? JSON.parse(str) : fallback; }
  catch { return fallback; }
};

const getRainColor = (pct: number | null): string => {
  if (pct === null) return '#94a3b8';
  if (pct >= 70) return '#ef4444';
  if (pct >= 40) return '#f59e0b';
  return '#22c55e';
};

const SEASON_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  peak:     { bg: '#fff1f0', border: '#ffccc7', text: '#cf1322', badge: '#ff4d4f' },
  shoulder: { bg: '#fffbe6', border: '#ffe58f', text: '#d46b08', badge: '#faad14' },
  off_peak: { bg: '#f6ffed', border: '#b7eb8f', text: '#389e0d', badge: '#52c41a' },
  unknown:  { bg: '#f5f5f5', border: '#d9d9d9', text: '#595959', badge: '#8c8c8c' },
};

// ── Component ─────────────────────────────────────────────────────────────────
export default function ResultScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<LocalSearchParams>();

  const plan         = safeParseJson<any>(params.data, null);
  const weather      = params.weather || '';
  const mapUrl       = params.map_url || '';
  const weatherDays  = safeParseJson<WeatherDay[]>(params.weather_days, []);
  const seasonInfo   = safeParseJson<SeasonInfo>(params.season_info,  {} as SeasonInfo);
  const budgetRef    = safeParseJson<BudgetRef>(params.budget_ref,    {} as BudgetRef);
  const alternatives = safeParseJson<Alternative[]>(params.alternatives, []);

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
    if (mapUrl) Linking.openURL(mapUrl).catch(() => Alert.alert('Error', 'Could not open Google Maps.'));
  };

  const displayWeather = () => {
    if (!weather || weather.length < 2) return 'Unavailable';
    const parts = weather.split(',');
    return parts.length >= 2 ? parts[1].trim() : weather;
  };

  const calculateTotal = () => {
    if (!plan.budget_breakdown) return '0';
    let total = 0;
    Object.entries(plan.budget_breakdown).forEach(([key, value]) => {
      if (key !== 'total') {
        const amount = parseFloat(String(value).replace(/[^0-9.]/g, ''));
        if (!isNaN(amount)) total += amount;
      }
    });
    return total.toLocaleString();
  };

  const seasonColors = SEASON_COLORS[seasonInfo?.season] || SEASON_COLORS.unknown;

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

        {/* ── 1. Trip Summary ─────────────────────────────────────────────── */}
        <View style={styles.summaryCard}>
          <Text style={styles.tripTitle}>{plan.title}</Text>
          <View style={styles.durationRow}>
            <Ionicons name="calendar-outline" size={14} color="#888" />
            <Text style={styles.duration}>{plan.duration}</Text>
          </View>
        </View>

        {/* ── 2. Multi-Day Weather Forecast ──────────────────────────────── */}
        <View style={styles.weatherCard}>
          {/* Header */}
          <View style={styles.liveHeaderRow}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
              <Ionicons name="partly-sunny" size={20} color="#FFD700" />
              <Text style={styles.weatherTitle}>Trip Weather Forecast</Text>
            </View>
            <View style={styles.liveBadgeSmall}>
              <View style={styles.liveDot} />
              <Text style={styles.liveBadgeSmallText}>LIVE</Text>
            </View>
          </View>

          {weatherDays.length > 0 ? (
            <>
              {/* Horizontal scrollable day strip */}
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.dayStripContainer}
              >
                {weatherDays.map((day, idx) => (
                  <View
                    key={idx}
                    style={[
                      styles.dayCard,
                      !day.available && styles.dayCardUnavailable,
                    ]}
                  >
                    <Text style={styles.dayNum}>{day.day_num}</Text>
                    <Text style={styles.dayLabel}>{day.day_label}</Text>
                    <Text style={styles.dayEmoji}>{day.emoji}</Text>
                    {day.available ? (
                      <>
                        <Text style={styles.dayTemp}>{day.temp}°C</Text>
                        <Text style={styles.dayRange}>{day.temp_min}° / {day.temp_max}°</Text>
                        <Text style={styles.dayDesc} numberOfLines={2}>{day.description}</Text>
                        <View style={styles.rainRow}>
                          <Ionicons name="rainy-outline" size={11} color={getRainColor(day.rain_pct)} />
                          <Text style={[styles.rainText, { color: getRainColor(day.rain_pct) }]}>
                            {day.rain_pct}%
                          </Text>
                        </View>
                        {(day.humidity !== null) && (
                          <Text style={styles.humidityText}>💧 {day.humidity}%</Text>
                        )}
                      </>
                    ) : (
                      <Text style={styles.unavailableText}>No forecast{"\n"}available</Text>
                    )}
                  </View>
                ))}
              </ScrollView>

              {/* Legend */}
              <View style={styles.weatherLegend}>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#22c55e' }]} />
                  <Text style={styles.legendText}>Low rain (&lt;40%)</Text>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#f59e0b' }]} />
                  <Text style={styles.legendText}>Moderate (40–70%)</Text>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, { backgroundColor: '#ef4444' }]} />
                  <Text style={styles.legendText}>High (&gt;70%)</Text>
                </View>
              </View>
            </>
          ) : (
            /* Fallback: plain text if no structured data */
            <>
              <Text style={styles.weatherTempLarge}>{weather.split(',')[1]?.trim() ?? weather}</Text>
              <Text style={styles.weatherDetailText}>{weather}</Text>
            </>
          )}
          <Text style={styles.sourceText}>📡 Source: OpenWeatherMap Forecast API (5-day / 3-hour)</Text>
        </View>

        {/* ── 3. Peak / Off-Peak Season Intelligence ──────────────────────── */}
        {seasonInfo?.label && (
          <View style={[styles.seasonCard, { backgroundColor: seasonColors.bg, borderColor: seasonColors.border }]}>
            <View style={styles.seasonHeaderRow}>
              <Text style={styles.seasonIcon}>{seasonInfo.icon || '📅'}</Text>
              <View style={{ flex: 1 }}>
                <Text style={[styles.seasonLabel, { color: seasonColors.text }]}>{seasonInfo.label}</Text>
                <Text style={styles.seasonRegion}>{seasonInfo.region} · {seasonInfo.month}</Text>
              </View>
              <View style={[styles.seasonBadge, { backgroundColor: seasonColors.badge }]}>
                <Text style={styles.seasonBadgeText}>{seasonInfo.season?.toUpperCase()}</Text>
              </View>
            </View>

            <View style={styles.seasonDivider} />

            <View style={styles.seasonInfoRow}>
              <Ionicons name="pricetag-outline" size={14} color={seasonColors.text} />
              <Text style={[styles.seasonImpact, { color: seasonColors.text }]}>
                Price Impact: {seasonInfo.price_impact}
              </Text>
            </View>

            <Text style={styles.seasonTip}>{seasonInfo.tip}</Text>
            <Text style={styles.sourceText}>📊 Source: {seasonInfo.source}</Text>
          </View>
        )}

        {/* ── 4. Google Maps Button ───────────────────────────────────────── */}
        <TouchableOpacity style={styles.mapButton} onPress={openMap}>
          <Ionicons name="map" size={20} color="#fff" style={{ marginRight: 8 }} />
          <Text style={styles.mapButtonText}>View Route on Google Maps</Text>
        </TouchableOpacity>

        {/* ── 5. Daily Itinerary ──────────────────────────────────────────── */}
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

        {/* ── 6. Budget Breakdown + Market Validation ─────────────────────── */}
        {plan.budget_breakdown && (
          <View style={styles.budgetCard}>
            <View style={styles.budgetHeaderRow}>
              <Text style={styles.budgetTitle}>💰 Budget Breakdown</Text>
              <View style={styles.aiEstimatedBadge}>
                <Text style={styles.aiEstimatedText}>AI Generated</Text>
              </View>
            </View>

            {/* AI breakdown bars */}
            <View style={styles.breakdownContainer}>
              {Object.entries(plan.budget_breakdown).map(([key, value], index) => {
                if (key === 'total') return null;
                const totalAmt = parseFloat(String(plan.budget_breakdown.total || calculateTotal()).replace(/[^0-9.]/g, '')) || 1;
                const cleanVal = parseFloat(String(value).replace(/[^0-9.]/g, '')) || 0;
                const pct      = Math.min(100, Math.max(0, (cleanVal / totalAmt) * 100));
                const colors   = ['#4ade80', '#60a5fa', '#f472b6', '#fbbf24', '#a78bfa'];
                const barColor = colors[index % colors.length];
                return (
                  <View key={key} style={styles.budgetRow}>
                    <View style={styles.budgetRowHeader}>
                      <Text style={styles.budgetItem}>{key.charAt(0).toUpperCase() + key.slice(1)}</Text>
                      <Text style={styles.budgetCost}>{String(value)} LKR</Text>
                    </View>
                    <View style={styles.chartBarBackground}>
                      <View style={[styles.chartBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                    </View>
                  </View>
                );
              })}
            </View>
            <View style={styles.divider} />
            <View style={styles.totalRow}>
              <Text style={styles.budgetLabel}>Total Estimated Cost</Text>
              <Text style={styles.budgetAmount}>LKR {calculateTotal()}</Text>
            </View>

            {/* Market Validation Section */}
            {budgetRef?.references && (
              <View style={styles.marketValidationBox}>
                <View style={styles.marketHeaderRow}>
                  <Ionicons name="checkmark-circle" size={16} color="#4ade80" />
                  <Text style={styles.marketTitle}>Market Validation</Text>
                  <View style={styles.tierBadge}>
                    <Text style={styles.tierBadgeText}>{budgetRef.tier_label}</Text>
                  </View>
                </View>
                <Text style={styles.marketNote}>{budgetRef.validation_note}</Text>

                {budgetRef.references.map((ref, i) => (
                  <View key={i} style={styles.refRow}>
                    <View style={styles.refLeft}>
                      <Text style={styles.refCategory}>{ref.category}</Text>
                      <Text style={styles.refRange}>{ref.market_range}</Text>
                    </View>
                    <Text style={styles.refSource} numberOfLines={2}>📎 {ref.source}</Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* ── 7. Alternative Destination Suggestions ──────────────────────── */}
        {alternatives.length > 0 && (
          <View style={styles.altCard}>
            <View style={styles.altHeaderRow}>
              <Ionicons name="compass" size={20} color="#007AFF" />
              <Text style={styles.altTitle}>You Might Also Like</Text>
            </View>
            <Text style={styles.altSubtitle}>Based on your selected interests</Text>
            {alternatives.map((alt, i) => (
              <View key={i} style={styles.altItem}>
                <View style={styles.altItemLeft}>
                  <Text style={styles.altName}>{alt.name}</Text>
                  <Text style={styles.altReason}>{alt.reason}</Text>
                  <Text style={styles.altDesc} numberOfLines={2}>{alt.description}</Text>
                </View>
                <View style={[styles.altCategoryBadge]}>
                  <Text style={styles.altCategoryText}>{alt.category}</Text>
                </View>
              </View>
            ))}
          </View>
        )}

      </ScrollView>
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const shadow = (h: number, op: number, r: number) => Platform.select({
  web:     { boxShadow: `0px ${h}px ${r}px rgba(0,0,0,${op})` } as any,
  default: { shadowColor: '#000', shadowOffset: { width: 0, height: h }, shadowOpacity: op, shadowRadius: r, elevation: Math.round(h * 1.5) },
});

const styles = StyleSheet.create({
  container:       { flex: 1, backgroundColor: '#f8f9fa' },
  errorContainer:  { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32, gap: 12 },
  errorTitle:      { fontSize: 22, fontWeight: '700', color: '#333' },
  errorSub:        { fontSize: 14, color: '#888', textAlign: 'center' },
  backBtnLarge:    { marginTop: 12, backgroundColor: '#007AFF', paddingVertical: 12, paddingHorizontal: 28, borderRadius: 12 },
  backBtnText:     { color: '#fff', fontWeight: '600', fontSize: 15 },

  header: {
    paddingTop: 52, paddingBottom: 14, paddingHorizontal: 16,
    backgroundColor: '#fff', flexDirection: 'row', alignItems: 'center',
    justifyContent: 'space-between', borderBottomWidth: 1, borderBottomColor: '#eee',
  },
  backButton:  { padding: 6 },
  headerTitle: { fontSize: 18, fontWeight: '700', color: '#1a1a2e' },
  scrollContent: { padding: 18, paddingBottom: 60 },

  // Trip Summary
  summaryCard: {
    backgroundColor: '#fff', borderRadius: 18, padding: 18, marginBottom: 12,
    ...shadow(3, 0.08, 8),
  },
  tripTitle:   { fontSize: 19, fontWeight: '800', color: '#007AFF', marginBottom: 6 },
  durationRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  duration:    { color: '#888', fontSize: 13 },

  // Live Weather — multiday
  weatherCard: {
    backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 14,
    borderWidth: 1, borderColor: '#e2e8f0', ...shadow(2, 0.04, 6),
  },
  liveHeaderRow:       { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  weatherTitle:        { fontWeight: '700', color: '#1e293b', fontSize: 14 },
  liveBadgeSmall:      { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fee2e2', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, gap: 4 },
  liveDot:             { width: 6, height: 6, borderRadius: 3, backgroundColor: '#ef4444' },
  liveBadgeSmallText:  { color: '#ef4444', fontSize: 10, fontWeight: '800' },
  weatherTempLarge:    { fontSize: 24, fontWeight: '800', color: '#0f172a', marginBottom: 2 },
  weatherDetailText:   { color: '#64748b', fontSize: 13, lineHeight: 20, marginBottom: 6 },
  sourceText:          { fontSize: 10, color: '#94a3b8', fontStyle: 'italic', marginTop: 4 },

  // Day strip
  dayStripContainer: { paddingVertical: 10, paddingHorizontal: 2, gap: 10 },
  dayCard: {
    width: 110, backgroundColor: '#f0f6ff', borderRadius: 14, padding: 12,
    alignItems: 'center', borderWidth: 1, borderColor: '#dbeafe',
  },
  dayCardUnavailable: { backgroundColor: '#f5f5f5', borderColor: '#e5e5e5' },
  dayNum:   { fontSize: 10, fontWeight: '700', color: '#007AFF', marginBottom: 1 },
  dayLabel: { fontSize: 10, color: '#64748b', marginBottom: 6, textAlign: 'center' },
  dayEmoji: { fontSize: 28, marginBottom: 6 },
  dayTemp:  { fontSize: 22, fontWeight: '800', color: '#0f172a' },
  dayRange: { fontSize: 10, color: '#64748b', marginTop: 2, marginBottom: 4 },
  dayDesc:  { fontSize: 10, color: '#475569', textAlign: 'center', lineHeight: 13, marginBottom: 4 },
  rainRow:  { flexDirection: 'row', alignItems: 'center', gap: 3, marginTop: 2 },
  rainText: { fontSize: 11, fontWeight: '700' },
  humidityText: { fontSize: 10, color: '#94a3b8', marginTop: 2 },
  unavailableText: { fontSize: 10, color: '#bbb', textAlign: 'center', lineHeight: 14, marginTop: 6 },

  // Weather legend
  weatherLegend: { flexDirection: 'row', gap: 12, marginTop: 10, flexWrap: 'wrap' },
  legendItem:    { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot:     { width: 8, height: 8, borderRadius: 4 },
  legendText:    { fontSize: 10, color: '#94a3b8' },

  // Season Card
  seasonCard: {
    borderRadius: 16, padding: 16, marginBottom: 14,
    borderWidth: 1.5, ...shadow(2, 0.06, 6),
  },
  seasonHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  seasonIcon:      { fontSize: 26 },
  seasonLabel:     { fontSize: 16, fontWeight: '800' },
  seasonRegion:    { fontSize: 12, color: '#666', marginTop: 1 },
  seasonBadge:     { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  seasonBadgeText: { color: '#fff', fontSize: 10, fontWeight: '800' },
  seasonDivider:   { height: 1, backgroundColor: 'rgba(0,0,0,0.08)', marginBottom: 10 },
  seasonInfoRow:   { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  seasonImpact:    { fontSize: 13, fontWeight: '700' },
  seasonTip:       { fontSize: 13, color: '#444', lineHeight: 19, marginBottom: 6 },

  // Map
  mapButton: {
    backgroundColor: '#34C759', padding: 15, borderRadius: 14,
    flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginBottom: 22,
    ...shadow(2, 0.12, 5),
  },
  mapButtonText: { color: '#fff', fontWeight: '700', fontSize: 16 },

  // Itinerary
  sectionTitle:   { fontSize: 19, fontWeight: '800', marginBottom: 14, color: '#1a1a2e' },
  activityCard:   { flexDirection: 'row', marginBottom: 16 },
  timeColumn:     { alignItems: 'center', marginRight: 14, width: 52 },
  timeText:       { fontWeight: '700', color: '#007AFF', fontSize: 12, textAlign: 'center' },
  line:           { width: 2, flex: 1, backgroundColor: '#ddd', marginTop: 6 },
  detailsColumn:  {
    flex: 1, backgroundColor: '#fff', padding: 14, borderRadius: 14,
    ...shadow(2, 0.05, 6),
  },
  locationName: { fontSize: 15, fontWeight: '700', marginBottom: 4, color: '#1a1a2e' },
  description:  { color: '#666', fontSize: 13, lineHeight: 19 },
  dayBadge:     {
    marginTop: 8, alignSelf: 'flex-start',
    backgroundColor: '#f0f4ff', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6,
  },
  dayBadgeText: { fontSize: 11, color: '#007AFF', fontWeight: '600' },

  // Budget
  budgetCard: {
    backgroundColor: '#1a1a2e', padding: 20, borderRadius: 18, marginTop: 10, marginBottom: 14,
    ...shadow(4, 0.2, 10),
  },
  budgetHeaderRow:   { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  budgetTitle:       { color: '#fff', fontSize: 18, fontWeight: '800' },
  aiEstimatedBadge:  { backgroundColor: 'rgba(74,222,128,0.2)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6, borderWidth: 1, borderColor: '#4ade80' },
  aiEstimatedText:   { color: '#4ade80', fontSize: 10, fontWeight: '700', textTransform: 'uppercase' },
  breakdownContainer: { gap: 14 },
  budgetRow:         { flexDirection: 'column', gap: 6 },
  budgetRowHeader:   { flexDirection: 'row', justifyContent: 'space-between' },
  budgetItem:        { color: '#e2e8f0', fontSize: 14, fontWeight: '600' },
  budgetCost:        { color: '#fff', fontWeight: '600', fontSize: 14 },
  chartBarBackground: { height: 8, backgroundColor: '#334155', borderRadius: 4, width: '100%', overflow: 'hidden' },
  chartBarFill:      { height: '100%', borderRadius: 4 },
  divider:           { height: 1, backgroundColor: '#334155', marginVertical: 18 },
  totalRow:          { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  budgetLabel:       { color: '#94a3b8', fontSize: 14, fontWeight: '500' },
  budgetAmount:      { color: '#4ade80', fontSize: 24, fontWeight: '800' },

  // Market Validation
  marketValidationBox: {
    backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 12,
    padding: 14, borderWidth: 1, borderColor: 'rgba(255,255,255,0.1)',
  },
  marketHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  marketTitle:     { color: '#e2e8f0', fontSize: 13, fontWeight: '700', flex: 1 },
  tierBadge:       { backgroundColor: '#3b82f6', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10 },
  tierBadgeText:   { color: '#fff', fontSize: 10, fontWeight: '700' },
  marketNote:      { color: '#94a3b8', fontSize: 12, lineHeight: 17, marginBottom: 12 },
  refRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start',
    paddingVertical: 8, borderTopWidth: 1, borderTopColor: 'rgba(255,255,255,0.06)', gap: 8,
  },
  refLeft:     { flex: 1 },
  refCategory: { color: '#e2e8f0', fontSize: 13, fontWeight: '600' },
  refRange:    { color: '#4ade80', fontSize: 12, fontWeight: '700', marginTop: 2 },
  refSource:   { color: '#64748b', fontSize: 10, flex: 1.2, textAlign: 'right', lineHeight: 14 },

  // Alternatives
  altCard: {
    backgroundColor: '#fff', borderRadius: 18, padding: 18, marginBottom: 14,
    borderWidth: 1.5, borderColor: '#e0ecff', ...shadow(3, 0.07, 8),
  },
  altHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 4 },
  altTitle:     { fontSize: 17, fontWeight: '800', color: '#1a1a2e' },
  altSubtitle:  { fontSize: 12, color: '#888', marginBottom: 14 },
  altItem: {
    flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between',
    paddingVertical: 12, borderTopWidth: 1, borderTopColor: '#f0f0f0', gap: 10,
  },
  altItemLeft:      { flex: 1 },
  altName:          { fontSize: 15, fontWeight: '700', color: '#1a1a2e', marginBottom: 2 },
  altReason:        { fontSize: 11, color: '#007AFF', fontWeight: '600', marginBottom: 4 },
  altDesc:          { fontSize: 12, color: '#666', lineHeight: 17 },
  altCategoryBadge: { backgroundColor: '#eff6ff', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12, alignSelf: 'flex-start', marginTop: 2 },
  altCategoryText:  { fontSize: 11, color: '#007AFF', fontWeight: '700' },
});