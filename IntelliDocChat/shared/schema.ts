import { z } from "zod";

export const chatMessageSchema = z.object({
  role: z.enum(["user", "assistant"]),
  content: z.string(),
});

export const simplifiedSessionResponseSchema = z.object({
  content: z.string(),
  current_stage: z.string(),
});

export const userInputRequestSchema = z.object({
  user_input: z.string(),
});

export const folderSchema = z.object({
  id: z.string(),
  name: z.string(),
  created_at: z.string().optional(),
  last_activity: z.string().optional(),
});

export type ChatMessage = z.infer<typeof chatMessageSchema>;
export type SimplifiedSessionResponse = z.infer<typeof simplifiedSessionResponseSchema>;
export type UserInputRequest = z.infer<typeof userInputRequestSchema>;
export type Folder = z.infer<typeof folderSchema>;