export type ToneType = "Natural" | "Playful" | "Thoughtful" | "Flirty";

export interface Reply {
  tone: string;
  text: string;
  explanation: string;
}

export interface GenerateRequest {
  message: string;
  tone: ToneType;
  chat_history?: string;
  their_profile?: string;
  my_profile?: string;
  my_style?: string;
}

export interface GenerateResponse {
  success: boolean;
  replies: Reply[];
  provider: string;
}

export interface CoachRequest {
  message: string;
  chat_history?: string;
  context?: string;
}

export interface CoachResponse {
  success: boolean;
  vibe: string;
  subtext: string;
  interest_level: string;
  recommended_strategy: string;
  avoid: string[];
  provider: string;
}

export interface TranscribeResponse {
  success: boolean;
  transcript: string;
  language?: string;
  model?: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
  providers: Record<string, boolean>;
}

// Get base URL from environment or fall back to relative path (handled by proxy or ingress)
const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.vite_api_base_url ||
  ""
).replace(/\/$/, "");

async function handleResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMessage =
      data?.error ||
      data?.detail ||
      (typeof data === "string" ? data : `Request failed with status ${response.status}`);
    throw new Error(typeof errorMessage === "string" ? errorMessage : JSON.stringify(errorMessage));
  }

  return data as T;
}

export const api = {
  async testConnection(): Promise<{ success: boolean; message: string; product: string }> {
    const res = await fetch(`${API_BASE_URL}/api/test`);
    return handleResponse(res);
  },

  async checkHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse(res);
  },

  async generateReplies(payload: GenerateRequest): Promise<GenerateResponse> {
    const res = await fetch(`${API_BASE_URL}/api/generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<GenerateResponse>(res);
  },

  async coachConversation(payload: CoachRequest): Promise<CoachResponse> {
    const res = await fetch(`${API_BASE_URL}/api/coach`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    return handleResponse<CoachResponse>(res);
  },

  async transcribeAudio(file: File | Blob, filename = "audio.wav"): Promise<TranscribeResponse> {
    const formData = new FormData();
    formData.append("audio_file", file, filename);

    const res = await fetch(`${API_BASE_URL}/api/transcribe`, {
      method: "POST",
      body: formData,
    });
    return handleResponse<TranscribeResponse>(res);
  },
};
