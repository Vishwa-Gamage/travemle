import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/context/AuthContext';

export default function RegisterScreen() {
  const router = useRouter();
  const { register } = useAuth();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!username.trim() || !email.trim() || !password || !password2) {
      Alert.alert('Missing Fields', 'Please fill in all fields.');
      return;
    }
    if (password !== password2) {
      Alert.alert('Password Mismatch', 'Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      Alert.alert('Weak Password', 'Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    const result = await register(username.trim(), email.trim(), password, password2);
    setLoading(false);
    if (!result.success) {
      Alert.alert('Registration Failed', result.error || 'Please try again.');
    }
    // Navigation handled by the auth guard in app/_layout.tsx
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">

        {/* Header */}
        <View style={styles.header}>
          <View style={styles.logoRow}>
            <Ionicons name="location-sharp" size={36} color="#007AFF" />
            <Text style={styles.logoText}>Travemle</Text>
          </View>
          <Text style={styles.tagline}>Start your journey today</Text>
        </View>

        {/* Card */}
        <View style={styles.card}>
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.subtitle}>Join thousands of travellers</Text>

          {/* Username */}
          <Text style={styles.label}>Username</Text>
          <View style={styles.inputRow}>
            <Ionicons name="person-outline" size={20} color="#999" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              placeholder="Choose a username"
              placeholderTextColor="#bbb"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          {/* Email */}
          <Text style={styles.label}>Email</Text>
          <View style={styles.inputRow}>
            <Ionicons name="mail-outline" size={20} color="#999" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="your@email.com"
              placeholderTextColor="#bbb"
              keyboardType="email-address"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>

          {/* Password */}
          <Text style={styles.label}>Password</Text>
          <View style={styles.inputRow}>
            <Ionicons name="lock-closed-outline" size={20} color="#999" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="At least 6 characters"
              placeholderTextColor="#bbb"
              secureTextEntry={!showPass}
              autoCapitalize="none"
            />
            <TouchableOpacity onPress={() => setShowPass(!showPass)}>
              <Ionicons name={showPass ? 'eye-off-outline' : 'eye-outline'} size={20} color="#999" />
            </TouchableOpacity>
          </View>

          {/* Confirm Password */}
          <Text style={styles.label}>Confirm Password</Text>
          <View style={styles.inputRow}>
            <Ionicons name="shield-checkmark-outline" size={20} color="#999" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              value={password2}
              onChangeText={setPassword2}
              placeholder="Re-enter password"
              placeholderTextColor="#bbb"
              secureTextEntry={!showPass}
              autoCapitalize="none"
            />
          </View>

          {/* Register Button */}
          <TouchableOpacity
            style={[styles.btn, loading && styles.btnDisabled]}
            onPress={handleRegister}
            disabled={loading}
          >
            {loading
              ? <ActivityIndicator color="#fff" />
              : <Text style={styles.btnText}>Create Account</Text>
            }
          </TouchableOpacity>

          {/* Login link */}
          <TouchableOpacity onPress={() => router.back()} style={styles.linkRow}>
            <Text style={styles.linkText}>Already have an account? </Text>
            <Text style={styles.link}>Sign In</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f4ff' },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  header: { alignItems: 'center', marginBottom: 32 },
  logoRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  logoText: { fontSize: 36, fontWeight: '800', color: '#007AFF', marginLeft: 8 },
  tagline: { color: '#666', fontSize: 15 },
  card: {
    backgroundColor: '#fff', borderRadius: 24, padding: 28,
    elevation: 8,
    ...Platform.select({
      web: { boxShadow: '0px 8px 16px rgba(0, 0, 0, 0.10)' } as any,
      default: {
        shadowColor: '#000', shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.1, shadowRadius: 16,
      },
    }),
  },
  title: { fontSize: 26, fontWeight: '700', color: '#1a1a2e', marginBottom: 4 },
  subtitle: { color: '#888', fontSize: 14, marginBottom: 24 },
  label: { fontSize: 13, fontWeight: '600', color: '#444', marginBottom: 8, marginTop: 16 },
  inputRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#f8f9fa', borderRadius: 12, borderWidth: 1.5,
    borderColor: '#e8e8e8', paddingHorizontal: 14, height: 52, marginBottom: 4,
  },
  inputIcon: { marginRight: 10 },
  input: { flex: 1, fontSize: 16, color: '#333' },
  btn: {
    backgroundColor: '#007AFF', borderRadius: 14, height: 52,
    alignItems: 'center', justifyContent: 'center', marginTop: 24,
  },
  btnDisabled: { opacity: 0.6 },
  btnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  linkRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 20 },
  linkText: { color: '#888', fontSize: 14 },
  link: { color: '#007AFF', fontSize: 14, fontWeight: '600' },
});
