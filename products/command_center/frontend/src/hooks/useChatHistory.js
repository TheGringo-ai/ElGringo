import { useState, useCallback } from 'react';

const STORAGE_KEY = 'elgringo-command-chat';
const MAX_MESSAGES = 100;

function loadMessages() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMessages(messages) {
  try {
    const trimmed = messages.slice(-MAX_MESSAGES);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch {
    // storage full, clear old messages
    localStorage.removeItem(STORAGE_KEY);
  }
}

export default function useChatHistory() {
  const [messages, setMessages] = useState(loadMessages);

  const addMessage = useCallback((role, content) => {
    setMessages((prev) => {
      const next = [...prev, { role, content, ts: Date.now() }];
      saveMessages(next);
      return next;
    });
  }, []);

  const updateLastAssistant = useCallback((content) => {
    setMessages((prev) => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i--) {
        if (next[i].role === 'assistant') {
          next[i] = { ...next[i], content };
          break;
        }
      }
      saveMessages(next);
      return next;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { messages, addMessage, updateLastAssistant, clearHistory };
}
