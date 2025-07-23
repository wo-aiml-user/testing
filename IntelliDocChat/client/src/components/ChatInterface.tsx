import { useState, useRef, useEffect } from "react";
import { useChat } from "../hooks/useChat";
import { useToast } from "@/lib/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { 
  Plus, 
  Send, 
  Mic, 
  Share, 
  Bot, 
  User,
  Upload,
  Folder as FolderIcon,
  Trash2
} from "lucide-react";
import { cn } from "@/lib/utils";

export function ChatInterface() {
  const {
    activeSessionId,
    folders,
    chatHistory,
    currentStage,
    isUploading,
    isSendingMessage,
    uploadError,
    uploadFile,
    sendMessage,
    sendInitialChatInput,
    sendVoiceMessage,
    selectFolder,
    createNewChat,
    deleteFolder,
    getActiveFolder,
  } = useChat();

  const { toast } = useToast();
  const [inputValue, setInputValue] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const isProcessing = isUploading || isSendingMessage;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, isProcessing]);

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const handleFileUpload = (file: File) => {
    if (file.type === "application/pdf") {
      uploadFile(file);
    } else {
      toast({
        description: "Please upload a PDF file.",
        variant: "destructive",
      });
    }
  };

  const handleSendMessage = () => {
    if (inputValue.trim() && activeSessionId) {
      if (!chatHistory.length && !isUploading) {
        sendInitialChatInput(inputValue.trim());
      } else {
        sendMessage(inputValue.trim());
      }
      setInputValue("");
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleMicClick = async () => {
    if (!activeSessionId) {
      toast({
        description: "Please select or create a chat session first.",
        variant: "destructive",
      });
      return;
    }

    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mediaRecorder = new MediaRecorder(stream);
        mediaRecorderRef.current = mediaRecorder;
        audioChunksRef.current = [];

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            audioChunksRef.current.push(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
          if (audioBlob.size < 1000) {
            toast({
              description: "Audio recording is too short or empty.",
              variant: "destructive",
            });
          } else {
            try {
              await sendVoiceMessage(audioBlob);
            } catch (error: any) {
              toast({
                description: `Failed to process voice input: ${error.message}`,
                variant: "destructive",
              });
            }
          }
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        setIsRecording(true);
        setTimeout(() => {
          if (isRecording && mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
          }
        }, 30000);
      } catch (error) {
        toast({
          description: "Could not access microphone. Please check permissions.",
          variant: "destructive",
        });
      }
    } else {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        setIsRecording(false);
      }
    }
  };

  const activeFolder = getActiveFolder();
  const hasChatStarted = chatHistory.length > 0 || isUploading;

  return (
    <div className="flex h-screen bg-[var(--chat-background)] text-[var(--chat-text-primary)]">
      <input
        type="file"
        ref={fileInputRef}
        onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
        accept=".pdf"
        className="hidden"
      />
      
      <div className="w-80 chat-sidebar border-r border-[var(--chat-border)] flex flex-col">
        <div className="p-4 border-b border-[var(--chat-border)]">
          <Button
            onClick={createNewChat}
            className="w-full bg-[var(--chat-accent)] hover:bg-[var(--chat-accent)]/90 text-white"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-medium text-[var(--chat-text-secondary)]">Folders</h2>
            </div>
            
            <div className="space-y-1">
              {folders.map((folder) => (
                <div
                  key={folder.id}
                  onClick={() => selectFolder(folder.id)}
                  className={cn(
                    "group folder-item flex items-center space-x-3 p-3 rounded-lg cursor-pointer",
                    activeSessionId === folder.id
                      ? "active bg-[var(--chat-background)]"
                      : "hover:bg-[var(--chat-background)]"
                  )}
                >
                  <FolderIcon className="w-4 h-4 text-[var(--chat-text-secondary)] flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{folder.name}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteFolder(folder.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        <div className="chat-sidebar border-b border-[var(--chat-border)] p-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">
              {activeFolder?.name || "New Project"}
            </h2>
            <p className="text-sm text-[var(--chat-text-secondary)]">Work Scope Generator</p>
          </div>
          <Button variant="ghost" size="icon" className="text-[var(--chat-text-secondary)]">
            <Share className="w-4 h-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-thin">
          {!activeSessionId ? (
            <div className="h-full flex flex-col items-center justify-center p-8 text-center">
              <div className="w-16 h-16 bg-[var(--chat-accent)] rounded-2xl flex items-center justify-center mb-4 mx-auto">
                  <Bot className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-semibold mb-2">How can I help you today?</h3>
              <p className="text-[var(--chat-text-secondary)] text-lg">Click "+ New Chat" in the sidebar to begin.</p>
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {!hasChatStarted && !isProcessing && (
                  <div className="h-full flex flex-col items-center justify-center p-8 text-center">
                      <div className="w-16 h-16 bg-[var(--chat-accent)] rounded-2xl flex items-center justify-center mb-4 mx-auto">
                        <Upload className="w-8 h-8 text-white" />
                      </div>
                      <h3 className="text-2xl font-semibold mb-2">Start Your Project</h3>
                      <p className="text-[var(--chat-text-secondary)] text-lg mb-8">
                        Describe your project in the input box below, or upload a document to begin.
                      </p>
                      <Button
                        onClick={() => fileInputRef.current?.click()}
                        className="bg-[var(--chat-accent)] hover:bg-[var(--chat-accent)]/90 text-white"
                        size="lg"
                        disabled={isProcessing}
                      >
                        <Upload className="w-4 h-4 mr-2" />
                        'Upload Document'
                      </Button>
                      {uploadError && <p className="mt-4 text-red-400">Error: {uploadError.message}</p>}
                  </div>
              )}

              {chatHistory.map((message, index) => (
                <div
                  key={index}
                  className={cn(
                    "flex items-start space-x-3 message-animation",
                    message.role === "user" ? "justify-end" : ""
                  )}
                >
                  {message.role === "assistant" && (
                    <div className="w-8 h-8 bg-[var(--chat-accent)] rounded-lg flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 text-white" />
                    </div>
                  )}
                  
                  <div className="flex-1 flex justify-end">
                    <div className={cn(
                      "rounded-lg p-4 max-w-3xl",
                      message.role === "user" 
                        ? "chat-message-user ml-auto" 
                        : "chat-message-assistant mr-auto"
                    )}>
                      <p className="leading-relaxed whitespace-pre-wrap">
                        {message.content}
                      </p>
                    </div>
                  </div>
                  
                  {message.role === "user" && (
                    <div className="w-8 h-8 bg-[var(--chat-border)] rounded-lg flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 text-[var(--chat-text-secondary)]" />
                    </div>
                  )}
                </div>
              ))}
              
              {isProcessing && !isUploading && (
                <div className="flex items-start space-x-3 message-animation">
                  <div className="w-8 h-8 bg-[var(--chat-accent)] rounded-lg flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="chat-message-assistant rounded-lg p-4 max-w-3xl">
                      <div className="flex items-center space-x-2">
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-[var(--chat-accent)] border-t-transparent"></div>
                        <p className="text-[var(--chat-text-secondary)] text-sm">
                          Thinking...
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              {isRecording && (
                <div className="flex items-start space-x-3 message-animation">
                  <div className="w-8 h-8 bg-[var(--chat-accent)] rounded-lg flex items-center justify-center flex-shrink-0">
                    <Mic className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="chat-message-assistant rounded-lg p-4 max-w-3xl">
                      <div className="flex items-center space-x-2">
                        <div className="animate-pulse rounded-full h-4 w-4 bg-red-500"></div>
                        <p className="text-[var(--chat-text-secondary)] text-sm">
                          Recording audio...
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="chat-sidebar border-t border-[var(--chat-border)] p-4">
          <div className="flex items-center space-x-3">
            <div className="flex-1 relative">
              <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Describe your project or provide feedback..."
                disabled={!activeSessionId || isProcessing}
                className="chat-input pr-12"
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={handleMicClick}
                className={cn(
                  "absolute right-2 top-1/2 transform -translate-y-1/2",
                  isRecording
                    ? "text-red-500 hover:text-red-600"
                    : "text-[var(--chat-text-secondary)] hover:text-[var(--chat-text-primary)]"
                )}
              >
                <Mic className="w-4 h-4" />
              </Button>
            </div>
            <Button
              onClick={handleSendMessage}
              disabled={!activeSessionId || !inputValue.trim() || isProcessing}
              className="bg-[var(--chat-accent)] hover:bg-[var(--chat-accent)]/90 text-white"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          
          <div className="flex items-center justify-between mt-3 text-xs text-[var(--chat-text-secondary)]">
            <div className="flex items-center space-x-4">
              <span>
                {activeSessionId ? `Session active` : "No active session"}
              </span>
              {activeSessionId && (
                <>
                  <span>•</span>
                  <span>Current stage: {currentStage}</span>
                </>
              )}
            </div>
            <div className="flex items-center space-x-2">
              <span>Press Enter to send</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}