export type MessageRole = "USER" | "ASSISTANT" | "SYSTEM";
export type ProposedActionStatus =
  | "PENDING"
  | "APPROVED"
  | "REJECTED"
  | "EXECUTED";

export interface AssistantMessage {
  id: number;
  role: MessageRole;
  content: string;
  tool_calls: unknown[] | null;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  model_used: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: AssistantMessage[];
}

export interface ProposedAction {
  id: number;
  conversation_id: number;
  message_id: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  summary: string;
  status: ProposedActionStatus;
  decided_by_id: number | null;
  decided_at: string | null;
  result: Record<string, unknown> | null;
  created_at: string;
}

export interface ChatResponse {
  conversation_id: number;
  assistant_text: string;
  model_used: string;
  proposed_actions: ProposedAction[];
}
