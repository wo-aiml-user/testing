import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { nanoid } from "nanoid";
import { api } from "../lib/api";
import type { ChatMessage, Folder } from "@shared/schema";

type ChatStore = Record<string, ChatMessage[]>;

function getStoredState<T>(key: string, defaultValue: T): T {
  const savedItem = localStorage.getItem(key);
  if (savedItem) {
    try {
      return JSON.parse(savedItem);
    } catch (e) {
      console.error("Failed to parse stored state for key:", key, e);
      return defaultValue;
    }
  }
  return defaultValue;
}

export function useChat() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(() => 
    getStoredState<string | null>("activeSessionId", null)
  );
  const [folders, setFolders] = useState<Folder[]>(() =>
    getStoredState<Folder[]>("folders", [])
  );
  const [allChats, setAllChats] = useState<ChatStore>(() =>
    getStoredState<ChatStore>("allChats", {})
  );
  const [currentStage, setCurrentStage] = useState<string>("overview");

  useEffect(() => {
    localStorage.setItem("activeSessionId", JSON.stringify(activeSessionId));
  }, [activeSessionId]);

  useEffect(() => {
    localStorage.setItem("folders", JSON.stringify(folders));
  }, [folders]);
  
  useEffect(() => {
    localStorage.setItem("allChats", JSON.stringify(allChats));
  }, [allChats]);

  const uploadFileMutation = useMutation({
    mutationFn: api.uploadFile,
    onSuccess: (data, variables) => {
      const assistantMessage: ChatMessage = { role: 'assistant', content: data.content };
      setAllChats(prev => ({ ...prev, [variables.sessionId]: [assistantMessage] }));
      setCurrentStage(data.current_stage);
      
      const file = variables.file;
      const folderName = file.name.replace(/\.pdf$/i, "").replace(/[_-]/g, " ");
      const capitalizedName = folderName.charAt(0).toUpperCase() + folderName.slice(1);
      setFolders(prev => prev.map(f => f.id === variables.sessionId ? { ...f, name: capitalizedName } : f));
    },
    onError: (error, variables) => {
      const errorMessage: ChatMessage = { role: 'assistant', content: `Error during upload: ${error.message}` };
      setAllChats(prev => ({ ...prev, [variables.sessionId]: [errorMessage] }));
    }
  });

  const sendMessageMutation = useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      api.sendMessage(sessionId, message),
    onSuccess: (data, variables) => {
      const assistantMessage: ChatMessage = { role: 'assistant', content: data.content };
      setAllChats(prev => {
        const currentHistory = prev[variables.sessionId] || [];
        return { ...prev, [variables.sessionId]: [...currentHistory, assistantMessage] };
      });
      setCurrentStage(data.current_stage);
    },
    onError: (error, variables) => {
        const errorMessage: ChatMessage = { role: 'assistant', content: `Error sending message: ${error.message}` };
        setAllChats(prev => {
            const currentHistory = prev[variables.sessionId] || [];
            return { ...prev, [variables.sessionId]: [...currentHistory, errorMessage] };
        });
    }
  });

  const sendInitialChatInputMutation = useMutation({
    mutationFn: ({ sessionId, input }: { sessionId: string; input: string }) =>
      api.sendInitialChatInput(sessionId, input),
    onSuccess: (data, variables) => {
      const assistantMessage: ChatMessage = { role: 'assistant', content: data.content };
      setAllChats(prev => ({ ...prev, [variables.sessionId]: [ ...prev[variables.sessionId], assistantMessage] }));
      setCurrentStage(data.current_stage);
      
      const folderName = variables.input.split('\n')[0].slice(0, 50).trim() || "New Project";
      const capitalizedName = folderName.charAt(0).toUpperCase() + folderName.slice(1);
      setFolders(prev => prev.map(f => f.id === variables.sessionId ? { ...f, name: capitalizedName } : f));
    },
    onError: (error, variables) => {
      const errorMessage: ChatMessage = { role: 'assistant', content: `Error processing input: ${error.message}` };
      setAllChats(prev => ({ ...prev, [variables.sessionId]: [errorMessage] }));
    }
  });

  const sendVoiceMessageMutation = useMutation({
    mutationFn: ({ sessionId, audioBlob }: { sessionId: string; audioBlob: Blob }) =>
      api.sendVoiceMessage(sessionId, audioBlob),
    onSuccess: (data, variables) => {
      const userMessage: ChatMessage = { role: 'user', content: data.transcribed_text || "[Voice Input]" };
      const assistantMessage: ChatMessage = { role: 'assistant', content: data.content };
      
      setAllChats(prev => {
        const currentHistory = prev[variables.sessionId] || [];
        const optimisticHistory = currentHistory.filter(m => m.content !== "[Processing voice...]");
        return { ...prev, [variables.sessionId]: [...optimisticHistory, userMessage, assistantMessage] };
      });
      setCurrentStage(data.current_stage);

      const chatHistory = allChats[variables.sessionId] || [];
      if (chatHistory.length === 0 && data.transcribed_text) {
          const folderName = data.transcribed_text.split('\n')[0].slice(0, 50).trim() || "New Voice Project";
          const capitalizedName = folderName.charAt(0).toUpperCase() + folderName.slice(1);
          setFolders(prev => prev.map(f => f.id === variables.sessionId ? { ...f, name: capitalizedName } : f));
      }
    },
    onError: (error, variables) => {
        const errorMessage: ChatMessage = { role: 'assistant', content: `Error processing voice: ${error.message}` };
        setAllChats(prev => {
            const currentHistory = prev[variables.sessionId] || [];
            const optimisticHistory = currentHistory.filter(m => m.content !== "[Processing voice...]");
            return { ...prev, [variables.sessionId]: [...optimisticHistory, errorMessage] };
        });
    }
  });

  const sendVoiceMessage = (audioBlob: Blob) => {
    if (activeSessionId) {
      const placeholderUserMessage: ChatMessage = { role: 'user', content: "[Processing voice...]" };
      setAllChats(prev => {
        const currentHistory = prev[activeSessionId] || [];
        return { ...prev, [activeSessionId]: [...currentHistory, placeholderUserMessage] };
      });
      sendVoiceMessageMutation.mutate({ sessionId: activeSessionId, audioBlob });
    }
  };

  const createNewChat = () => {
    const newSessionId = nanoid();
    const newFolder: Folder = {
      id: newSessionId,
      name: "New Project",
      created_at: new Date().toISOString(),
      last_activity: new Date().toISOString(),
    };
    
    setFolders(prev => [newFolder, ...prev]);
    setAllChats(prev => ({ ...prev, [newSessionId]: [] }));
    setActiveSessionId(newSessionId);
    setCurrentStage("initial");
  };

  const uploadFile = (file: File) => {
    if (!activeSessionId) {
      console.error("Cannot upload file, no active session ID");
      return;
    }
    uploadFileMutation.mutate({ file, sessionId: activeSessionId });
  };

  const sendMessage = (message: string) => {
    if (activeSessionId) {
      const userMessage: ChatMessage = { role: 'user', content: message };
      setAllChats(prev => {
        const currentHistory = prev[activeSessionId] || [];
        return { ...prev, [activeSessionId]: [...currentHistory, userMessage] };
      });
      sendMessageMutation.mutate({ sessionId: activeSessionId, message });
    }
  };

  const sendInitialChatInput = (input: string) => {
    if (activeSessionId) {
      const userMessage: ChatMessage = { role: 'user', content: input };
      setAllChats(prev => ({ ...prev, [activeSessionId]: [userMessage] }));
      sendInitialChatInputMutation.mutate({ sessionId: activeSessionId, input });
    }
  };
  
  const selectFolder = (folderId: string) => {
    setActiveSessionId(folderId);
  };
  
  const deleteFolder = (folderId: string) => {
    setFolders(prev => prev.filter(f => f.id !== folderId));
    setAllChats(prev => {
        const newChats = { ...prev };
        delete newChats[folderId];
        return newChats;
    });
    if (activeSessionId === folderId) {
        setActiveSessionId(null);
    }
  };
  
  const getActiveFolder = () => {
    return folders.find(folder => folder.id === activeSessionId) || null;
  };
  
  const chatHistory = allChats[activeSessionId || ''] || [];

  return {
    activeSessionId,
    folders,
    chatHistory,
    currentStage,
    isUploading: uploadFileMutation.isPending,
    isSendingMessage: sendMessageMutation.isPending || sendInitialChatInputMutation.isPending || sendVoiceMessageMutation.isPending,
    uploadError: uploadFileMutation.error,
    sendError: sendMessageMutation.error || sendInitialChatInputMutation.error || sendVoiceMessageMutation.error,
    uploadFile,
    sendMessage,
    sendInitialChatInput,
    sendVoiceMessage,
    selectFolder,
    createNewChat,
    deleteFolder,
    getActiveFolder,
  };
}