import { useState, useEffect, useRef } from "react";
import "./App.css";
import {
  api,
  type CoachResponse,
  type Reply,
  type ToneType,
} from "./services/api";
import { countWords, formatSeconds } from "./utils/formatters";

function App() {
  const [activeTab, setActiveTab] = useState<"wingman" | "coach" | "voice">("wingman");
  const [message, setMessage] = useState("");
  const [tone, setTone] = useState<ToneType>("Natural");

  // Advanced context (collapsible)
  const [showContext, setShowContext] = useState(false);
  const [chatHistory, setChatHistory] = useState("");
  const [theirProfile, setTheirProfile] = useState("");
  const [myProfile, setMyProfile] = useState("");
  const [myStyle, setMyStyle] = useState("");

  // Backend status
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "disconnected">("checking");

  // Wingman Reply Generation
  const [replies, setReplies] = useState<Reply[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [provider, setProvider] = useState("");

  // Coach Analysis
  const [coachData, setCoachData] = useState<CoachResponse | null>(null);
  const [coaching, setCoaching] = useState(false);
  const [coachError, setCoachError] = useState("");

  // Voice Notes & Recording
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [transcriptionStatus, setTranscriptionStatus] = useState("");
  const [transcriptionResult, setTranscriptionResult] = useState<{
    text: string;
    language?: string;
  } | null>(null);

  // Toast notifications
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "info" } | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const showToast = (message: string, type: "success" | "error" | "info" = "success") => {
    setToast({ message, type });
    setTimeout(() => {
      setToast((current) => (current?.message === message ? null : current));
    }, 3200);
  };

  // Check backend health on mount
  useEffect(() => {
    let isMounted = true;
    api
      .checkHealth()
      .then((data) => {
        if (isMounted) {
          if (data.status === "healthy") {
            setBackendStatus("connected");
          } else {
            setBackendStatus("disconnected");
          }
        }
      })
      .catch(() => {
        if (isMounted) setBackendStatus("disconnected");
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Cleanup audio preview URL on unmount or new recording
  useEffect(() => {
    return () => {
      if (recordedUrl) {
        URL.revokeObjectURL(recordedUrl);
      }
    };
  }, [recordedUrl]);

  // Handle Wingman Generation
  const handleGenerate = async () => {
    if (!message.trim()) {
      setGenerationError("Please enter a conversation message first.");
      return;
    }

    setGenerating(true);
    setGenerationError("");
    setReplies([]);

    try {
      const response = await api.generateReplies({
        message: message.trim(),
        tone,
        chat_history: chatHistory.trim() || undefined,
        their_profile: theirProfile.trim() || undefined,
        my_profile: myProfile.trim() || undefined,
        my_style: myStyle.trim() || undefined,
      });

      setReplies(response.replies);
      setProvider(response.provider);
      showToast("Generated 3 tailored replies!");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to generate replies.";
      setGenerationError(msg);
      showToast(msg, "error");
    } finally {
      setGenerating(false);
    }
  };

  // Handle Coach Analysis
  const handleCoach = async () => {
    if (!message.trim()) {
      setCoachError("Please paste a conversation snippet to analyze.");
      return;
    }

    setCoaching(true);
    setCoachError("");
    setCoachData(null);

    try {
      const response = await api.coachConversation({
        message: message.trim(),
        chat_history: chatHistory.trim() || undefined,
        context: theirProfile.trim() || undefined,
      });

      setCoachData(response);
      showToast("Conversation analysis complete!");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Analysis failed.";
      setCoachError(msg);
      showToast(msg, "error");
    } finally {
      setCoaching(false);
    }
  };

  // Copy reply to clipboard
  const copyReply = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      showToast("Reply copied to clipboard!");
    } catch {
      showToast("Could not copy automatically. Please select text manually.", "error");
    }
  };

  // Voice Recording Functions
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setRecordedBlob(audioBlob);
        if (recordedUrl) URL.revokeObjectURL(recordedUrl);
        setRecordedUrl(URL.createObjectURL(audioBlob));
        // Stop all audio tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      recorder.start();
      setIsRecording(true);
      setRecordingDuration(0);
      setTranscriptionStatus("");

      timerRef.current = window.setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Microphone access error:", err);
      showToast("Microphone permission denied or not supported.", "error");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  const handleTranscribe = async (targetBlob?: Blob, targetFilename?: string) => {
    const fileToUpload = targetBlob || recordedBlob || audioFile;
    if (!fileToUpload) {
      setTranscriptionStatus("Please record or select an audio file first.");
      return;
    }

    setTranscribing(true);
    setTranscriptionStatus("Transcribing audio with Gnani Prisma STT...");
    setTranscriptionResult(null);

    try {
      const filename = targetFilename || (audioFile ? audioFile.name : "voice_note.webm");
      const res = await api.transcribeAudio(fileToUpload, filename);

      setTranscriptionResult({
        text: res.transcript,
        language: res.language,
      });
      setTranscriptionStatus("Transcription completed successfully!");
      showToast("Audio transcribed!");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Transcription failed.";
      setTranscriptionStatus(`Error: ${msg}`);
      showToast(msg, "error");
    } finally {
      setTranscribing(false);
    }
  };

  const applyTranscription = (target: "wingman" | "coach") => {
    if (transcriptionResult) {
      setMessage(transcriptionResult.text);
      setActiveTab(target);
      showToast(`Transferred transcription to ${target === "wingman" ? "Wingman" : "Coach"}!`);
    }
  };



  return (
    <div className="app-shell">
      {/* Toast Notification */}
      {toast && (
        <div className={`toast toast-${toast.type}`} role="status">
          <span>{toast.type === "success" ? "✓" : toast.type === "error" ? "⚠" : "ℹ"}</span>
          <p>{toast.message}</p>
        </div>
      )}

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">w.</span>
          <span>wingman</span>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <button
          className={`nav-item ${activeTab === "wingman" ? "active" : ""}`}
          onClick={() => setActiveTab("wingman")}
        >
          <span>✳</span> Wingman
        </button>

        <button
          className={`nav-item ${activeTab === "coach" ? "active" : ""}`}
          onClick={() => setActiveTab("coach")}
        >
          <span>◈</span> Coach
        </button>

        <button
          className={`nav-item ${activeTab === "voice" ? "active" : ""}`}
          onClick={() => setActiveTab("voice")}
        >
          <span>◉</span> Voice notes
        </button>

        <div className="sidebar-bottom">
          <div className="profile-avatar">W</div>
          <div>
            <strong>Wingman Suite</strong>
            <p>Production Ready</p>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="topbar">
          <span>YOUR CONVERSATION SPACE</span>

          <div className="status">
            <span
              className="status-dot"
              style={{
                background:
                  backendStatus === "connected"
                    ? "#22c55e"
                    : backendStatus === "checking"
                    ? "#eab308"
                    : "#ef4444",
              }}
            ></span>
            {backendStatus === "connected"
              ? "Backend Active"
              : backendStatus === "checking"
              ? "Connecting..."
              : "Backend Offline"}
          </div>
        </header>

        {/* Hero Section */}
        <section className="hero">
          <div className="eyebrow">A LITTLE HELP WITH WORDS</div>
          <h1>
            Good conversations
            <br />
            <span>start with you.</span>
          </h1>
          <p>
            Sometimes you know what you want to say.
            <br />
            You just need a little help finding the words.
          </p>
        </section>

        {/* Workspace Container */}
        <section className="workspace">
          <div className="section-heading">
            <div>
              <h2>
                {activeTab === "wingman"
                  ? "Let's find your words."
                  : activeTab === "coach"
                  ? "Let's understand the conversation."
                  : "Let's work with your voice."}
              </h2>
              <p>
                {activeTab === "wingman"
                  ? "Share a message and we'll generate 3 natural human responses."
                  : activeTab === "coach"
                  ? "Understand subtext, mood, interest, and the best tactical strategy."
                  : "Record live or upload an audio note to transcribe with Gnani Prisma STT."}
              </p>
            </div>
            <span className="sparkle">✳</span>
          </div>

          {/* TAB 1: VOICE NOTES */}
          {activeTab === "voice" && (
            <div className="voice-container">
              {/* Live Audio Recorder */}
              <div className="composer voice-card">
                <label>OPTION 1: RECORD LIVE AUDIO</label>
                <div className="recorder-controls">
                  {!isRecording ? (
                    <button className="record-btn start-rec" onClick={startRecording}>
                      <span className="rec-dot"></span> Record Voice Note
                    </button>
                  ) : (
                    <button className="record-btn stop-rec" onClick={stopRecording}>
                      <span className="rec-square"></span> Stop Recording ({formatSeconds(recordingDuration)})
                    </button>
                  )}

                  {recordedUrl && !isRecording && (
                    <div className="audio-preview">
                      <audio controls src={recordedUrl} />
                      <button
                        className="generate-button transcribe-sub-btn"
                        onClick={() => handleTranscribe()}
                        disabled={transcribing}
                      >
                        {transcribing ? "Transcribing..." : "Transcribe Recording ↗"}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* File Upload Audio */}
              <div className="composer voice-card" style={{ marginTop: "20px" }}>
                <label>OPTION 2: UPLOAD AUDIO FILE</label>
                <input
                  type="file"
                  accept=".wav,.mp3,.ogg,.flac,.aac,.m4a,.webm,audio/*"
                  onChange={(e) => {
                    const file = e.target.files?.[0] || null;
                    setAudioFile(file);
                    setTranscriptionStatus("");
                    setTranscriptionResult(null);
                  }}
                  className="file-input"
                />

                {audioFile && (
                  <div className="file-info">
                    <span>
                      Selected: <strong>{audioFile.name}</strong> ({(audioFile.size / 1024 / 1024).toFixed(2)} MB)
                    </span>
                    <button
                      className="generate-button transcribe-sub-btn"
                      onClick={() => handleTranscribe(audioFile, audioFile.name)}
                      disabled={transcribing}
                    >
                      {transcribing ? "Transcribing..." : "Transcribe File ↗"}
                    </button>
                  </div>
                )}
              </div>

              {/* Transcription Status */}
              {transcriptionStatus && (
                <div className="transcription-status-box" role="status">
                  {transcribing && <span className="spinner"></span>}
                  <span>{transcriptionStatus}</span>
                </div>
              )}

              {/* Transcription Result Card */}
              {transcriptionResult && (
                <div className="transcription-result-card">
                  <div className="result-header">
                    <h3>Transcription Output</h3>
                    {transcriptionResult.language && (
                      <span className="lang-tag">Language: {transcriptionResult.language}</span>
                    )}
                  </div>
                  <p className="transcript-text">{transcriptionResult.text}</p>
                  <div className="transcript-actions">
                    <button className="apply-btn" onClick={() => applyTranscription("wingman")}>
                      Use in Wingman (Generate Replies) ↗
                    </button>
                    <button className="apply-btn outline" onClick={() => applyTranscription("coach")}>
                      Analyze in Coach ↗
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2 & 3: WINGMAN & COACH COMPOSER */}
          {activeTab !== "voice" && (
            <>
              {/* Message Input Box */}
              <div className="composer">
                <label>
                  {activeTab === "wingman" ? "WHAT DID THEY SAY?" : "CONVERSATION SNIPPET / MESSAGE"}
                </label>

                <textarea
                  value={message}
                  onChange={(e) => {
                    setMessage(e.target.value);
                    setGenerationError("");
                    setCoachError("");
                  }}
                  placeholder={
                    activeTab === "wingman"
                      ? "Paste the text you received (e.g., 'What are you up to this weekend?')..."
                      : "Paste the message or exchange you want to analyze..."
                  }
                  maxLength={5000}
                />

                <div className="composer-footer">
                  <span>Only share conversations you have permission to use.</span>
                  <span>{message.length} / 5000 characters</span>
                </div>
              </div>

              {/* Collapsible Context Section */}
              <div className="context-accordion">
                <button
                  type="button"
                  className="accordion-toggle"
                  onClick={() => setShowContext(!showContext)}
                >
                  <span>{showContext ? "▼ Hide conversation context" : "▶ Add optional context (chat history, profiles)"}</span>
                  <span className="context-hint">{showContext ? "Less" : "Tune tone & accuracy"}</span>
                </button>

                {showContext && (
                  <div className="accordion-content">
                    <div className="context-field">
                      <label>RECENT CHAT HISTORY (Optional)</label>
                      <textarea
                        rows={2}
                        value={chatHistory}
                        onChange={(e) => setChatHistory(e.target.value)}
                        placeholder="Oldest to newest messages..."
                      />
                    </div>
                    <div className="context-grid">
                      <div className="context-field">
                        <label>ABOUT THEM (Optional)</label>
                        <input
                          type="text"
                          value={theirProfile}
                          onChange={(e) => setTheirProfile(e.target.value)}
                          placeholder="e.g. Loves dogs, works in tech, witty"
                        />
                      </div>
                      <div className="context-field">
                        <label>ABOUT ME (Optional)</label>
                        <input
                          type="text"
                          value={myProfile}
                          onChange={(e) => setMyProfile(e.target.value)}
                          placeholder="e.g. Hiking, musician, busy weekdays"
                        />
                      </div>
                    </div>
                    {activeTab === "wingman" && (
                      <div className="context-field">
                        <label>MY TEXTING STYLE (Optional)</label>
                        <input
                          type="text"
                          value={myStyle}
                          onChange={(e) => setMyStyle(e.target.value)}
                          placeholder="e.g. Short sentences, lowercase, dry humor"
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* WINGMAN SPECIFIC: TONE SELECTION & GENERATE */}
              {activeTab === "wingman" && (
                <>
                  <div className="tone-section">
                    <label>HOW WOULD YOU LIKE TO RESPOND?</label>
                    <div className="tone-options">
                      {(["Natural", "Playful", "Thoughtful", "Flirty"] as ToneType[]).map((item) => (
                        <button
                          key={item}
                          className={`tone-button ${tone === item ? "selected" : ""}`}
                          onClick={() => {
                            setTone(item);
                            setReplies([]);
                          }}
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    className="generate-button"
                    onClick={handleGenerate}
                    disabled={!message.trim() || generating}
                  >
                    {generating ? (
                      <>
                        <span>Finding your words...</span>
                        <span className="spinner light"></span>
                      </>
                    ) : (
                      <>
                        <span>✳ Find my words</span>
                        <span>↗</span>
                      </>
                    )}
                  </button>

                  {generationError && (
                    <div role="alert" className="error-banner">
                      <span>⚠</span> {generationError}
                    </div>
                  )}

                  {/* Generated Replies Output */}
                  {replies.length > 0 && (
                    <div className="replies-grid">
                      <div className="replies-header">
                        <h2>Your suggested replies.</h2>
                        <p>
                          Generated via {provider}. Choose the one that sounds most like you.
                        </p>
                      </div>

                      {replies.map((reply, index) => (
                        <div key={index} className="reply-card">
                          <div className="reply-card-header">
                            <span className="option-badge">OPTION {index + 1}</span>
                            <span className="tone-badge">{reply.tone}</span>
                          </div>

                          <p className="reply-text">"{reply.text}"</p>
                          <p className="reply-explanation">{reply.explanation}</p>

                          <div className="reply-actions">
                            <button className="copy-btn" onClick={() => copyReply(reply.text)}>
                              📋 Copy reply
                            </button>
                            <span className="word-count">
                              {countWords(reply.text)} words
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* COACH SPECIFIC: ANALYZE & DISPLAY COACHING INSIGHTS */}
              {activeTab === "coach" && (
                <>
                  <button
                    className="generate-button"
                    onClick={handleCoach}
                    disabled={!message.trim() || coaching}
                    style={{ marginTop: "24px" }}
                  >
                    {coaching ? (
                      <>
                        <span>Analyzing conversation dynamics...</span>
                        <span className="spinner light"></span>
                      </>
                    ) : (
                      <>
                        <span>◈ Analyze Conversation</span>
                        <span>↗</span>
                      </>
                    )}
                  </button>

                  {coachError && (
                    <div role="alert" className="error-banner">
                      <span>⚠</span> {coachError}
                    </div>
                  )}

                  {coachData && (
                    <div className="coach-results">
                      <div className="coach-header">
                        <h2>Conversation Breakdown</h2>
                        <span className="provider-tag">Powered by {coachData.provider}</span>
                      </div>

                      <div className="coach-metrics">
                        <div className="metric-box">
                          <label>OVERALL VIBE</label>
                          <p className="metric-val">{coachData.vibe}</p>
                        </div>
                        <div className="metric-box">
                          <label>PERCEIVED INTEREST</label>
                          <span className={`interest-badge ${coachData.interest_level.toLowerCase()}`}>
                            {coachData.interest_level}
                          </span>
                        </div>
                      </div>

                      <div className="coach-card">
                        <div className="coach-card-title">
                          <span>🔍</span> What They Actually Mean (Subtext)
                        </div>
                        <p>{coachData.subtext}</p>
                      </div>

                      <div className="coach-card highlight">
                        <div className="coach-card-title">
                          <span>🎯</span> Recommended Tactical Strategy
                        </div>
                        <p>{coachData.recommended_strategy}</p>
                      </div>

                      {coachData.avoid && coachData.avoid.length > 0 && (
                        <div className="coach-card warning">
                          <div className="coach-card-title">
                            <span>🚫</span> What to Avoid
                          </div>
                          <ul className="avoid-list">
                            {coachData.avoid.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div className="coach-footer-action">
                        <button
                          className="generate-button"
                          onClick={() => {
                            setActiveTab("wingman");
                            showToast("Switched to Wingman. Choose your tone to generate replies!");
                          }}
                        >
                          <span>Generate replies based on this strategy</span>
                          <span>↗</span>
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}

          <div className="bottom-note">
            <span>✦</span>
            Your voice. Your choice. Always.
          </div>
        </section>

        <footer>
          WINGMAN © 2026
          <span>BUILT FOR BETTER CONVERSATIONS</span>
        </footer>
      </main>
    </div>
  );
}

export default App;
