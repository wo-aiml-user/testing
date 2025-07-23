import { apiRequest } from "./queryClient";
import type { SimplifiedSessionResponse, UserInputRequest } from "@shared/schema";

const API_BASE = "/api";

export const api = {
  uploadFile: async ({ file, sessionId }: { file: File; sessionId: string }): Promise<SimplifiedSessionResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/upload`, {
      method: "POST",
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Upload failed: ${response.statusText}`);
    }
    
    return response.json();
  },

  sendMessage: async (sessionId: string, userInput: string): Promise<SimplifiedSessionResponse> => {
    const response = await apiRequest(
      "POST",
      `${API_BASE}/sessions/${sessionId}/input`,
      { user_input: userInput } as UserInputRequest
    );
    
    return response.json();
  },

  sendVoiceMessage: async (sessionId: string, audioBlob: Blob): Promise<SimplifiedSessionResponse> => {
    const formData = new FormData();
    formData.append("audio_file", audioBlob, "voice.wav");

    const response = await fetch(`${API_BASE}/sessions/${sessionId}/voice-input`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Voice input failed: ${errorText}`);
    }

    return response.json();
  },
};
