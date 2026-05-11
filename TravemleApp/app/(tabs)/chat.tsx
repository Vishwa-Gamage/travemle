import React, { useState, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  ActivityIndicator,
  Keyboard,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import api from '@/services/api';
import { ENDPOINTS } from '@/constants/config';

type Message = {
  id: string;
  text: string;
  sender: 'user' | 'bot';
};

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-msg',
      text: "Hi there! I'm your Travemle AI Assistant. How can I help you plan your next trip?",
      sender: 'bot',
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);

  const sendMessage = async () => {
    if (!inputText.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      text: inputText.trim(),
      sender: 'user',
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsLoading(true);
    Keyboard.dismiss();

    try {
      const response = await api.post(ENDPOINTS.chat, {
        message: userMsg.text,
      });

      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: response.data.reply,
        sender: 'bot',
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        text: 'Sorry, I am having trouble connecting right now. Please try again later.',
        sender: 'bot',
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Ionicons name="chatbubbles" size={24} color="#007AFF" />
        <Text style={styles.headerTitle}>Travel Assistant <Text style={styles.betaBadge}>BETA</Text></Text>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        {/* Messages List */}
        <ScrollView
          ref={scrollViewRef}
          contentContainerStyle={styles.scrollContent}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {messages.map((msg) => (
            <View
              key={msg.id}
              style={[
                styles.messageBubble,
                msg.sender === 'user' ? styles.userBubble : styles.botBubble,
              ]}
            >
              <Text
                style={[
                  styles.messageText,
                  msg.sender === 'user' ? styles.userText : styles.botText,
                ]}
              >
                {msg.text}
              </Text>
            </View>
          ))}

          {isLoading && (
            <View style={[styles.messageBubble, styles.botBubble, styles.typingIndicator]}>
              <ActivityIndicator size="small" color="#007AFF" />
              <Text style={[styles.messageText, styles.botText, { marginLeft: 8 }]}>Thinking...</Text>
            </View>
          )}
        </ScrollView>

        {/* Input Area */}
        <View style={styles.inputContainer}>
          <TextInput
            style={styles.textInput}
            value={inputText}
            onChangeText={setInputText}
            placeholder="Ask about destinations, budget, etc..."
            placeholderTextColor="#999"
            multiline
            maxLength={500}
          />
          <TouchableOpacity
            style={[styles.sendButton, !inputText.trim() && styles.sendButtonDisabled]}
            onPress={sendMessage}
            disabled={!inputText.trim() || isLoading}
          >
            <Ionicons name="send" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    elevation: 2,
    ...Platform.select({
      web: { boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.05)' } as any,
    }),
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#1a1a2e',
    marginLeft: 10,
  },
  betaBadge: {
    fontSize: 10,
    color: '#007AFF',
    fontWeight: '700',
    backgroundColor: '#e6f0ff',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
    overflow: 'hidden',
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 20,
  },
  messageBubble: {
    maxWidth: '80%',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
    marginBottom: 12,
  },
  userBubble: {
    backgroundColor: '#007AFF',
    alignSelf: 'flex-end',
    borderBottomRightRadius: 4,
  },
  botBubble: {
    backgroundColor: '#fff',
    alignSelf: 'flex-start',
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  messageText: {
    fontSize: 15,
    lineHeight: 22,
  },
  userText: {
    color: '#fff',
  },
  botText: {
    color: '#334155',
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#eee',
    alignItems: 'flex-end',
  },
  textInput: {
    flex: 1,
    backgroundColor: '#f1f5f9',
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
    fontSize: 15,
    maxHeight: 120,
    minHeight: 40,
    color: '#1e293b',
  },
  sendButton: {
    backgroundColor: '#007AFF',
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 10,
    marginBottom: 2,
  },
  sendButtonDisabled: {
    backgroundColor: '#94a3b8',
  },
});
