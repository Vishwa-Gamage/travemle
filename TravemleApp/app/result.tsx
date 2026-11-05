import React from 'react';
import {
  StyleSheet, Text, View, ScrollView, TouchableOpacity,
  Linking, Alert, Platform,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';

// ── Types ────────────────────────────────────────────────────────────────────
type LocalSearchParams = {
  data:          string;
  weather:       string;
  map_url:       string;
  weather_days:  string;
  weather_alert: string;
  season_info:   string;
  budget_ref:    string;
  alternatives:  string;
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

interface WeatherAlertPlace {
  name:         string;
  category:     string;
  description:  string;
  region:       string;
  weather_note: string;
  reason:       string;
}

interface WeatherAlert {
  is_rainy:       boolean;
  avg_rain_pct?:  number;
  rainy_days?:    number;
  total_days?:    number;
  message?:       string;
  source?:        string;
  alternatives?:  WeatherAlertPlace[];
  better_regions?: Array<{ region: string; region_label: string; season: string }>;
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

  const plan          = safeParseJson<any>(params.data, null);
  const weather       = params.weather || '';
  const mapUrl        = params.map_url || '';
  const weatherDays   = safeParseJson<WeatherDay[]>(params.weather_days,   []);
  const weatherAlert  = safeParseJson<WeatherAlert>(params.weather_alert,  {} as WeatherAlert);
  const seasonInfo    = safeParseJson<SeasonInfo>(params.season_info,   {} as SeasonInfo);
  const budgetRef     = safeParseJson<BudgetRef>(params.budget_ref,     {} as BudgetRef);
  const alternatives  = safeParseJson<Alternative[]>(params.alternatives, []);

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
    if (plan.budget_breakdown.total) {
      return Number(plan.budget_breakdown.total).toLocaleString();
    }
    let total = 0;
    Object.entries(plan.budget_breakdown).forEach(([key, value]) => {
      if (key !== 'total' && key !== 'per_person') {
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
          <View style={styles.summaryTopRow}>
            <Text style={styles.tripTitle}>{plan.title}</Text>
            {plan.passenger_label && (
              <View style={styles.passengerBadge}>
                <Ionicons name="people" size={12} color="#007AFF" />
                <Text style={styles.passengerBadgeText}>{plan.passenger_label}</Text>
              </View>
            )}
          </View>
          <View style={styles.summaryMetaRow}>
            <View style={styles.durationRow}>
              <Ionicons name="calendar-outline" size={14} color="#888" />
              <Text style={styles.duration}>{plan.duration}</Text>
            </View>
            {plan.rooms_needed && (
              <View style={styles.durationRow}>
                <Ionicons name="bed-outline" size={14} color="#888" />
                <Text style={styles.duration}>{plan.rooms_needed} {plan.rooms_needed === 1 ? 'Room' : 'Rooms'}</Text>
              </View>
            )}
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
            {weatherDays.some(d => d.is_climate_avg) ? (
              <View style={[styles.liveBadgeSmall, { backgroundColor: '#eff6ff' }]}>
                <Ionicons name="calendar" size={11} color="#007AFF" />
                <Text style={[styles.liveBadgeSmallText, { color: '#007AFF' }]}>CLIMATE FORECAST</Text>
              </View>
            ) : (
              <View style={styles.liveBadgeSmall}>
                <View style={styles.liveDot} />
                <Text style={styles.liveBadgeSmallText}>LIVE 5-DAY</Text>
              </View>
            )}
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
                            {day.rain_pct}% rain
                          </Text>
                        </View>
                        {day.is_climate_avg && (
                          <View style={styles.climateTag}>
                            <Text style={styles.climateTagText}>Seasonal</Text>
                          </View>
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

        {/* ── 🌧️ Rainy-Day Alert & Drier-Region Recommendations ────────── */}
        {weatherAlert?.is_rainy && (
          <View style={styles.rainAlertCard}>
            {/* Alert header */}
            <View style={styles.rainAlertHeader}>
              <Text style={styles.rainAlertIcon}>🌧️</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.rainAlertTitle}>Heavy Rain Forecasted</Text>
                <Text style={styles.rainAlertSubtitle}>
                  {weatherAlert.rainy_days}/{weatherAlert.total_days} forecast days · Avg {weatherAlert.avg_rain_pct}% precipitation
                </Text>
              </View>
              <View style={styles.rainPctBadge}>
                <Text style={styles.rainPctBadgeText}>{weatherAlert.avg_rain_pct}%</Text>
              </View>
            </View>

            <View style={styles.rainDivider} />

            {/* Message */}
            <Text style={styles.rainAlertMessage}>{weatherAlert.message}</Text>

            {/* Better region alternatives */}
            {(weatherAlert.alternatives?.length ?? 0) > 0 && (
              <>
                <Text style={styles.rainAltTitle}>☀️ Consider These Instead</Text>
                {weatherAlert.alternatives!.map((place, i) => (
                  <View key={i} style={styles.rainAltItem}>
                    <View style={styles.rainAltTop}>
                      <Text style={styles.rainAltName}>{place.name}</Text>
                      <View style={styles.rainAltRegionBadge}>
                        <Text style={styles.rainAltRegionText}>{place.region}</Text>
                      </View>
                    </View>
                    <Text style={styles.rainAltWeatherNote}>{place.weather_note}</Text>
                    <Text style={styles.rainAltReason}>✓ {place.reason}</Text>
                    <Text style={styles.rainAltDesc} numberOfLines={2}>{place.description}</Text>
                  </View>
                ))}
              </>
            )}

            {weatherAlert.source && (
              <Text style={styles.sourceText}>📊 Source: {weatherAlert.source}</Text>
            )}
          </View>
        )}

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

        {/* ── 4.5. Recommended Accommodation ────────────────────────────── */}
        {plan.recommended_accommodation && (
          <View style={styles.hotelCard}>
            <View style={styles.hotelCardHeader}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Ionicons name="bed" size={20} color="#007AFF" />
                <Text style={styles.hotelCardTitle}>Recommended Accommodation</Text>
              </View>
              <View style={styles.hotelTypeBadge}>
                <Text style={styles.hotelTypeBadgeText}>
                  {String(plan.recommended_accommodation.accommodation_type || plan.recommended_accommodation.type || 'Hotel').replace('_', ' ').toUpperCase()}
                </Text>
              </View>
            </View>

            <View style={styles.hotelCardBody}>
              <View style={styles.hotelTopRow}>
                <Text style={styles.hotelName}>
                  {String(plan.recommended_accommodation.name || '').replace(/\s+\d+$/, '').trim() || 'Cozy Local Stay'}
                </Text>
                <View style={styles.hotelRatingBadge}>
                  <Ionicons name="star" size={13} color="#f59e0b" />
                  <Text style={styles.hotelRatingText}>
                    {plan.recommended_accommodation.rating ? Number(plan.recommended_accommodation.rating).toFixed(1) : '4.0'}
                  </Text>
                </View>
              </View>

              <Text style={styles.hotelPricePerNight}>
                LKR {Number(plan.recommended_accommodation.price_per_night || 0).toLocaleString()}
                <Text style={styles.hotelPriceSub}> / night</Text>
              </Text>

              {/* Total cost for trip duration & rooms */}
              <View style={styles.hotelStayCostBox}>
                <Ionicons name="calculator-outline" size={15} color="#007AFF" />
                <View style={{ flex: 1 }}>
                  <Text style={styles.hotelStayCostText}>
                    {plan.rooms_needed ? `${plan.rooms_needed} room${plan.rooms_needed > 1 ? 's' : ''} × ` : ''}
                    {plan.duration || 'trip'} @ LKR {Number(plan.recommended_accommodation.price_per_night || 0).toLocaleString()}/night
                  </Text>
                  <Text style={styles.hotelTotalHighlight}>
                    Total Accommodation: LKR {(
                      plan.budget_breakdown?.accommodation
                        ? Number(plan.budget_breakdown.accommodation).toLocaleString()
                        : (Number(plan.recommended_accommodation.price_per_night || 0) * (parseInt(plan.duration) || 1) * (plan.rooms_needed || 1)).toLocaleString()
                    )}
                  </Text>
                </View>
              </View>
            </View>
          </View>
        )}

        {/* ── 5. Daily Itinerary ──────────────────────────────────────────── */}
        <Text style={styles.sectionTitle}>Daily Itinerary</Text>
        {(() => {
          // Group activities by day label (e.g. "Day 1", "Day 2")
          const dayMap: Record<string, { date: string; items: any[] }> = {};
          (plan.activities || []).forEach((act: any) => {
            const key = act.day || 'Day 1';
            if (!dayMap[key]) dayMap[key] = { date: act.date || '', items: [] };
            dayMap[key].items.push(act);
          });

          const formatDate = (iso: string) => {
            if (!iso) return '';
            try {
              const [y, m, d] = iso.split('-').map(Number);
              const dt = new Date(y, m - 1, d);
              return dt.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
            } catch { return iso; }
          };

          // Use the 'type' field from backend: checkin → 🏨, checkout → 🚗, activity → ⏰
          const getRowIcon = (activity: any) => {
            if (activity.type === 'checkin')  return '🏨';
            if (activity.type === 'checkout') return '🚗';
            return '⏰';
          };

          return Object.entries(dayMap).map(([dayLabel, { date, items }], dayIdx) => (
            <View key={dayIdx} style={styles.dayCard}>
              {/* Day header bar with weather indicator */}
              <View style={styles.dayCardHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.dayCardNum}>{dayLabel}</Text>
                  {date ? (
                    <Text style={styles.dayCardDate}>{formatDate(date)}</Text>
                  ) : null}
                </View>
                {(() => {
                  const dayWeather = weatherDays.find(w => w.day_num === dayLabel || w.date === date);
                  if (!dayWeather || !dayWeather.available) return null;
                  return (
                    <View style={styles.itineraryDayWeatherPill}>
                      <Text style={{ fontSize: 16 }}>{dayWeather.emoji}</Text>
                      <View style={{ alignItems: 'flex-end' }}>
                        <Text style={styles.itineraryDayWeatherTemp}>{dayWeather.temp}°C</Text>
                        <Text style={styles.itineraryDayWeatherRain}>🌧️ {dayWeather.rain_pct}%</Text>
                      </View>
                    </View>
                  );
                })()}
              </View>

              {/* Schedule rows — "8:00 AM  Visit Nine Arch Bridge" */}
              {items.map((activity: any, idx: number) => (
                <View
                  key={idx}
                  style={[
                    styles.scheduleRow,
                    idx < items.length - 1 && styles.scheduleRowBorder,
                  ]}
                >
                  {/* Time pill */}
                  <View style={styles.scheduleTimePill}>
                    <Text style={styles.scheduleTimeIcon}>
                      {getRowIcon(activity)}
                    </Text>
                    <Text style={styles.scheduleTimeText}>{activity.time}</Text>
                  </View>

                  {/* Activity name + small subtitle */}
                  <View style={styles.scheduleBody}>
                    <Text style={styles.scheduleActivityName}>
                      {activity.location_name}
                    </Text>
                    {activity.description ? (
                      <Text style={styles.scheduleActivitySub}>
                        {activity.description}
                      </Text>
                    ) : null}
                  </View>
                </View>
              ))}
            </View>
          ));
        })()}

        {/* ── 6. Budget Breakdown (Simplified & Friendly Card) ─────────────── */}
        {plan.budget_breakdown && (
          <View style={styles.budgetCard}>
            {/* Header */}
            <View style={styles.budgetHeaderRow}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Text style={{ fontSize: 22 }}>💰</Text>
                <View>
                  <Text style={styles.budgetTitle}>Trip Cost Estimate</Text>
                  <Text style={styles.budgetSubtitle}>
                    {plan.passengers || 1} {(plan.passengers || 1) === 1 ? 'Person' : 'People'} · {plan.duration || 'Trip'}
                  </Text>
                </View>
              </View>
              <View style={styles.calculatedBadge}>
                <Ionicons name="sparkles" size={12} color="#93c5fd" />
                <Text style={styles.calculatedText}>ESTIMATE</Text>
              </View>
            </View>

            {/* Big Highlight Box: Input Budget vs Planned Cost & Coverage Badge */}
            <View style={styles.budgetHighlightHero}>
              <View style={styles.heroLeft}>
                <Text style={styles.heroTotalLabel}>Planned Trip Cost</Text>
                <Text style={styles.heroTotalValue}>LKR {calculateTotal()}</Text>
                {plan.input_budget ? (
                  <Text style={styles.heroBudgetCapSub}>
                    Your Budget: LKR {Number(plan.input_budget).toLocaleString()}
                  </Text>
                ) : null}
              </View>
              {(plan.passengers || 1) > 1 && plan.budget_breakdown?.per_person && (
                <View style={styles.heroRight}>
                  <Text style={styles.heroPerPersonLabel}>Each Person Pays</Text>
                  <Text style={styles.heroPerPersonValue}>
                    LKR {Number(plan.budget_breakdown.per_person).toLocaleString()}
                  </Text>
                </View>
              )}
            </View>

            {/* Budget Health / Status Banner */}
            {plan.input_budget ? (
              <View style={[
                styles.budgetStatusBanner,
                plan.is_covered ? styles.budgetStatusSuccess : styles.budgetStatusWarning
              ]}>
                <Ionicons
                  name={plan.is_covered ? "checkmark-circle" : "alert-circle"}
                  size={18}
                  color={plan.is_covered ? "#16a34a" : "#d97706"}
                />
                <View style={{ flex: 1 }}>
                  <Text style={[
                    styles.budgetStatusTitle,
                    { color: plan.is_covered ? "#15803d" : "#b45309" }
                  ]}>
                    {plan.is_covered ? "Covered within your budget!" : "Exceeds your budget"}
                  </Text>
                  <Text style={styles.budgetStatusSub}>
                    {plan.is_covered
                      ? (plan.savings_or_buffer > 0
                          ? `You will save ~LKR ${Number(plan.savings_or_buffer).toLocaleString()} as safety buffer.`
                          : "This entire itinerary is fitted directly to your target budget.")
                      : `Requires ~LKR ${Number(plan.budget_deficit).toLocaleString()} more for standard accommodation & meals.`}
                  </Text>
                </View>
              </View>
            ) : null}

            {/* Clear, Step-by-Step Expense List */}
            <Text style={styles.expenseSectionTitle}>Where does the money go?</Text>
            <View style={styles.breakdownCardsContainer}>
              {/* 1. Accommodation */}
              {plan.budget_breakdown?.accommodation ? (
                <View style={styles.expenseCardRow}>
                  <View style={[styles.expenseIconWrap, { backgroundColor: '#eff6ff' }]}>
                    <Text style={{ fontSize: 18 }}>🏨</Text>
                  </View>
                  <View style={styles.expenseDetailCol}>
                    <Text style={styles.expenseName}>Stay & Hotel</Text>
                    <Text style={styles.expenseSimpleMath}>
                      {plan.rooms_needed || 1} room{(plan.rooms_needed || 1) > 1 ? 's' : ''} for {plan.duration || 'trip'}
                    </Text>
                  </View>
                  <Text style={styles.expensePriceText}>
                    LKR {Number(plan.budget_breakdown.accommodation).toLocaleString()}
                  </Text>
                </View>
              ) : null}

              {/* 2. Food & Dining */}
              {plan.budget_breakdown?.food ? (
                <View style={styles.expenseCardRow}>
                  <View style={[styles.expenseIconWrap, { backgroundColor: '#fef3c7' }]}>
                    <Text style={{ fontSize: 18 }}>🍽️</Text>
                  </View>
                  <View style={styles.expenseDetailCol}>
                    <Text style={styles.expenseName}>Meals & Drinks</Text>
                    <Text style={styles.expenseSimpleMath}>
                      {(plan.passengers || 1) > 1 ? `${plan.passengers} people · ` : ''}3 meals/day
                    </Text>
                  </View>
                  <Text style={styles.expensePriceText}>
                    LKR {Number(plan.budget_breakdown.food).toLocaleString()}
                  </Text>
                </View>
              ) : null}

              {/* 3. Activities & Sightseeing */}
              {plan.budget_breakdown?.activities ? (
                <View style={styles.expenseCardRow}>
                  <View style={[styles.expenseIconWrap, { backgroundColor: '#f0fdf4' }]}>
                    <Text style={{ fontSize: 18 }}>🎟️</Text>
                  </View>
                  <View style={styles.expenseDetailCol}>
                    <Text style={styles.expenseName}>Tickets & Activities</Text>
                    <Text style={styles.expenseSimpleMath}>
                      Sightseeing & entrance fees
                    </Text>
                  </View>
                  <Text style={styles.expensePriceText}>
                    LKR {Number(plan.budget_breakdown.activities).toLocaleString()}
                  </Text>
                </View>
              ) : null}

              {/* 4. Travel & Transport */}
              {plan.budget_breakdown?.transport ? (
                <View style={styles.expenseCardRow}>
                  <View style={[styles.expenseIconWrap, { backgroundColor: '#faf5ff' }]}>
                    <Text style={{ fontSize: 18 }}>
                      {plan.preferred_transport === 'train' ? '🚆' : (plan.preferred_transport === 'bus' ? '🚌' : '🚗')}
                    </Text>
                  </View>
                  <View style={styles.expenseDetailCol}>
                    <Text style={styles.expenseName}>
                      {plan.preferred_transport === 'bus' || plan.preferred_transport === 'train' ? 'Public Transport' : 'Transport & Fuel'}
                    </Text>
                    <Text style={styles.expenseSimpleMath}>
                      {plan.budget_breakdown.transport_note || 'Travel for the entire trip'}
                    </Text>
                  </View>
                  <Text style={styles.expensePriceText}>
                    LKR {Number(plan.budget_breakdown.transport).toLocaleString()}
                  </Text>
                </View>
              ) : null}
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
  tripTitle:   { fontSize: 19, fontWeight: '800', color: '#007AFF', flex: 1, marginRight: 8 },
  summaryTopRow: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 },
  summaryMetaRow: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  durationRow: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  duration:    { color: '#888', fontSize: 13 },
  passengerBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#eff6ff',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#bfdbfe',
  },
  passengerBadgeText: { fontSize: 11, fontWeight: '700', color: '#007AFF' },
  perPersonSub: { fontSize: 11, color: '#64748b', marginTop: 2 },

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
  sourceText:          { fontSize: 10, color: '#64748b', fontStyle: 'italic', marginTop: 4 },

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
  humidityText: { fontSize: 10, color: '#64748b', marginTop: 2 },
  unavailableText: { fontSize: 10, color: '#bbb', textAlign: 'center', lineHeight: 14, marginTop: 6 },

  // Weather legend
  weatherLegend: { flexDirection: 'row', gap: 12, marginTop: 10, flexWrap: 'wrap' },
  legendItem:    { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot:     { width: 8, height: 8, borderRadius: 4 },
  legendText:    { fontSize: 10, color: '#64748b' },

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

  // ── Recommended Accommodation Card ───────────────────────────────────────
  hotelCard: {
    backgroundColor: '#fff', borderRadius: 16, marginBottom: 20,
    borderWidth: 1.5, borderColor: '#dbeafe', overflow: 'hidden', ...shadow(3, 0.08, 8),
  },
  hotelCardHeader: {
    backgroundColor: '#eff6ff', paddingHorizontal: 16, paddingVertical: 12,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    borderBottomWidth: 1, borderBottomColor: '#dbeafe',
  },
  hotelCardTitle:     { fontSize: 15, fontWeight: '700', color: '#1e3a8a' },
  hotelTypeBadge:     { backgroundColor: '#007AFF', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  hotelTypeBadgeText: { color: '#fff', fontSize: 10, fontWeight: '800' },
  hotelCardBody:      { padding: 16 },
  hotelTopRow:        { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 },
  hotelName:          { fontSize: 17, fontWeight: '800', color: '#0f172a', flex: 1, marginRight: 8 },
  hotelRatingBadge:   { flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: '#fef3c7', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  hotelRatingText:    { fontSize: 12, fontWeight: '800', color: '#b45309' },
  hotelPricePerNight: { fontSize: 20, fontWeight: '800', color: '#007AFF', marginBottom: 10 },
  hotelPriceSub:      { fontSize: 13, fontWeight: '500', color: '#64748b' },
  hotelStayCostBox:   { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: '#f8fafc', padding: 10, borderRadius: 8 },
  hotelStayCostText:  { fontSize: 11, color: '#64748b' },
  hotelTotalHighlight: { fontSize: 13, fontWeight: '700', color: '#0f172a', marginTop: 2 },
  budgetFormulaSub:   { fontSize: 10, color: '#64748b', marginTop: 1 },

  // ── Daily Itinerary – card-per-day layout ────────────────────────────────
  sectionTitle:   { fontSize: 19, fontWeight: '800', marginBottom: 14, color: '#1a1a2e' },

  // One card per day
  dayCard: {
    backgroundColor: '#fff', borderRadius: 16, marginBottom: 16,
    overflow: 'hidden', ...shadow(2, 0.07, 8),
  },
  dayCardHeader: {
    backgroundColor: '#007AFF', paddingHorizontal: 16, paddingVertical: 12,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  itineraryDayWeatherPill: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 8, paddingVertical: 4,
    borderRadius: 8,
  },
  itineraryDayWeatherTemp: { color: '#fff', fontSize: 13, fontWeight: '800' },
  itineraryDayWeatherRain: { color: 'rgba(255,255,255,0.9)', fontSize: 10, fontWeight: '600' },
  climateTag: {
    backgroundColor: '#dbeafe', paddingHorizontal: 6, paddingVertical: 2,
    borderRadius: 4, marginTop: 4,
  },
  climateTagText: { fontSize: 9, fontWeight: '700', color: '#1e40af', textTransform: 'uppercase' },
  dayCardNum:  { fontSize: 16, fontWeight: '800', color: '#fff' },
  dayCardDate: { fontSize: 12, color: 'rgba(255,255,255,0.85)', marginTop: 2, fontWeight: '500' },

  // Activity row inside the day card
  dayActivityRow: {
    flexDirection: 'row', alignItems: 'flex-start',
    paddingHorizontal: 16, paddingVertical: 14, gap: 14,
  },
  dayActivityRowBorder: { borderBottomWidth: 1, borderBottomColor: '#f0f4ff' },

  // ── Schedule row styles (replaces old time-label column) ──────────────
  scheduleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  scheduleRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: '#f0f4ff',
  },
  scheduleTimePill: {
    alignItems: 'center',
    width: 72,
    paddingTop: 2,
  },
  scheduleTimeIcon: { fontSize: 16, marginBottom: 3 },
  scheduleTimeText: {
    fontSize: 11,
    fontWeight: '800',
    color: '#007AFF',
    textAlign: 'center',
    letterSpacing: 0.2,
  },
  scheduleBody: { flex: 1 },
  scheduleActivityName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#1a1a2e',
    marginBottom: 2,
    lineHeight: 20,
  },
  scheduleActivitySub: {
    fontSize: 11,
    color: '#888',
    lineHeight: 16,
  },

  // Budget Card (User-Friendly Light Theme)
  budgetCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 20,
    marginTop: 10,
    marginBottom: 16,
    borderWidth: 1.5,
    borderColor: '#e2e8f0',
    ...shadow(3, 0.08, 10),
  },
  budgetHeaderRow:   { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  budgetTitle:       { color: '#0f172a', fontSize: 18, fontWeight: '800' },
  budgetSubtitle:    { color: '#64748b', fontSize: 12, marginTop: 1 },
  calculatedBadge:   { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: '#eff6ff', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, borderWidth: 1, borderColor: '#bfdbfe' },
  calculatedText:    { color: '#007AFF', fontSize: 10, fontWeight: '800', letterSpacing: 0.5 },

  // Hero Card for Total & Per-Person
  budgetHighlightHero: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#f0f9ff',
    borderRadius: 16,
    padding: 16,
    marginBottom: 18,
    borderWidth: 1.5,
    borderColor: '#bae6fd',
  },
  heroLeft: { flex: 1 },
  heroTotalLabel: { fontSize: 11, fontWeight: '700', color: '#0284c7', textTransform: 'uppercase', letterSpacing: 0.4 },
  heroTotalValue: { fontSize: 22, fontWeight: '900', color: '#0369a1', marginTop: 2 },
  heroBudgetCapSub: { fontSize: 11, fontWeight: '600', color: '#0284c7', marginTop: 3 },
  heroRight: {
    borderLeftWidth: 1,
    borderLeftColor: '#bae6fd',
    paddingLeft: 16,
    alignItems: 'flex-start',
  },
  heroPerPersonLabel: { fontSize: 11, fontWeight: '700', color: '#0284c7', textTransform: 'uppercase', letterSpacing: 0.4 },
  heroPerPersonValue: { fontSize: 18, fontWeight: '800', color: '#0f172a', marginTop: 2 },

  // Budget Status Banner
  budgetStatusBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    borderWidth: 1,
  },
  budgetStatusSuccess: {
    backgroundColor: '#f0fdf4',
    borderColor: '#bbf7d0',
  },
  budgetStatusWarning: {
    backgroundColor: '#fffbeb',
    borderColor: '#fde68a',
  },
  budgetStatusTitle: {
    fontSize: 13,
    fontWeight: '800',
  },
  budgetStatusSub: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 1,
  },

  // Section title & cards
  expenseSectionTitle: { fontSize: 13, fontWeight: '700', color: '#475569', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.4 },
  breakdownCardsContainer: { gap: 10, marginBottom: 14 },
  expenseCardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f8fafc',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  expenseIconWrap: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  expenseDetailCol: { flex: 1 },
  expenseName: { fontSize: 14, fontWeight: '700', color: '#1e293b' },
  expenseSimpleMath: { fontSize: 11, color: '#64748b', marginTop: 2 },
  expensePriceText: { fontSize: 15, fontWeight: '800', color: '#0f172a' },

  // Market Validation
  marketValidationBox: {
    backgroundColor: '#f8fafc', borderRadius: 14,
    padding: 14, borderWidth: 1, borderColor: '#e2e8f0', marginTop: 6,
  },
  marketHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 },
  marketTitle:     { color: '#1e293b', fontSize: 13, fontWeight: '700', flex: 1 },
  tierBadge:       { backgroundColor: '#3b82f6', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 10 },
  tierBadgeText:   { color: '#fff', fontSize: 10, fontWeight: '700' },
  marketNote:      { color: '#64748b', fontSize: 12, lineHeight: 17, marginBottom: 12 },
  refRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start',
    paddingVertical: 8, borderTopWidth: 1, borderTopColor: '#e2e8f0', gap: 8,
  },
  refLeft:     { flex: 1 },
  refCategory: { color: '#1e293b', fontSize: 13, fontWeight: '600' },
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

  // ── Rainy-Day Alert Card ──────────────────────────────────────────────────
  rainAlertCard: {
    backgroundColor: '#1e1b4b', borderRadius: 18, padding: 18, marginBottom: 14,
    borderWidth: 1.5, borderColor: '#4f46e5', ...shadow(4, 0.18, 10),
  },
  rainAlertHeader:   { flexDirection: 'row', alignItems: 'flex-start', gap: 10, marginBottom: 2 },
  rainAlertIcon:     { fontSize: 28 },
  rainAlertTitle:    { color: '#e0e7ff', fontSize: 16, fontWeight: '800' },
  rainAlertSubtitle: { color: '#a5b4fc', fontSize: 12, marginTop: 2 },
  rainPctBadge:      { backgroundColor: '#4f46e5', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 10 },
  rainPctBadgeText:  { color: '#fff', fontSize: 14, fontWeight: '800' },
  rainDivider:       { height: 1, backgroundColor: 'rgba(255,255,255,0.1)', marginVertical: 12 },
  rainAlertMessage:  { color: '#c7d2fe', fontSize: 13, lineHeight: 19, marginBottom: 14 },
  rainAltTitle:      { color: '#e0e7ff', fontSize: 14, fontWeight: '800', marginBottom: 10 },
  rainAltItem: {
    backgroundColor: 'rgba(255,255,255,0.06)', borderRadius: 12,
    padding: 12, marginBottom: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.08)',
  },
  rainAltTop:        { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 },
  rainAltName:       { color: '#fff', fontSize: 14, fontWeight: '700', flex: 1 },
  rainAltRegionBadge: { backgroundColor: '#4f46e5', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  rainAltRegionText: { color: '#c7d2fe', fontSize: 10, fontWeight: '700' },
  rainAltWeatherNote:{ color: '#a5b4fc', fontSize: 11, marginBottom: 3, lineHeight: 15 },
  rainAltReason:     { color: '#86efac', fontSize: 11, fontWeight: '600', marginBottom: 4 },
  rainAltDesc:       { color: '#64748b', fontSize: 11, lineHeight: 15 },
});