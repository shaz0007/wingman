
import { useState } from "react";
import "./App.css";

interface Reply {
  tone: string;
  text: string;
  explanation: string;
}

function App() {
  const [message, setMessage] = useState("");
  const [activeTab, setActiveTab] = useState("wingman");
  const [tone, setTone] = useState("Natural");

  const [connection, setConnection] = useState("Not tested");
  const [testing, setTesting] = useState(false);

  // AI generation states
  const [replies, setReplies] = useState<Reply[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState("");
  const [provider, setProvider] = useState("");

  // Voice transcription states
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [transcribing, setTranscribing] = useState(false);
  const [transcriptionStatus, setTranscriptionStatus] = useState("");

  // Test backend connection
  const testBackend = async () => {
    setTesting(true);
    setConnection("Connecting...");

    try {
      const response = await fetch("http://localhost:8000/api/test");

      if (!response.ok) {
        throw new Error("Backend request failed");
      }

      const data = await response.json();
      setConnection(data.message);
    } catch (error) {
      console.error("Backend error:", error);
      setConnection("Backend connection failed");
    } finally {
      setTesting(false);
    }
  };

  // Generate replies using Gemini or Groq
  const generateReplies = async () => {
    if (!message.trim()) {
      setGenerationError("Please enter a conversation message first.");
      return;
    }

    setGenerating(true);
    setGenerationError("");
    setReplies([]);
    setProvider("");

    try {
      const response = await fetch(
        "http://localhost:8000/api/generate",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            message: message.trim(),
            tone: tone
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Could not generate replies. Please try again."
        );
      }

      if (!Array.isArray(data.replies) || data.replies.length !== 3) {
        throw new Error("The AI did not return three valid replies.");
      }

      setReplies(data.replies);
      setProvider(data.provider || "AI");
    } catch (error) {
      console.error("Reply generation error:", error);

      setGenerationError(
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setGenerating(false);
    }
  };

  // Copy a suggested reply
  const copyReply = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      alert("Reply copied!");
    } catch (error) {
      console.error("Copy failed:", error);
      setGenerationError("Could not copy the reply. Please select it manually.");
    }
  };

  // Transcribe voice note using Gnani Prisma
  const transcribeAudio = async () => {
    if (!audioFile) {
      setTranscriptionStatus("Please select an audio file first.");
      return;
    }

    setTranscribing(true);
    setTranscriptionStatus("");

    try {
      const formData = new FormData();
      formData.append("audio_file", audioFile);

      const response = await fetch(
        "http://localhost:8000/api/transcribe",
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : JSON.stringify(data.detail || "Transcription failed")
        );
      }

      if (!data.transcript) {
        throw new Error("No transcription was returned.");
      }

      setMessage(data.transcript);
      setTranscriptionStatus(
        `Transcription successful! Language: ${data.language || "Detected"}`
      );

      setReplies([]);
      setGenerationError("");
      setActiveTab("wingman");
    } catch (error) {
      console.error("Transcription error:", error);

      setTranscriptionStatus(
        error instanceof Error
          ? error.message
          : "Something went wrong during transcription."
      );
    } finally {
      setTranscribing(false);
    }
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-icon">w.</span>
          <span>wingman</span>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <button
          className={`nav-item ${
            activeTab === "wingman" ? "active" : ""
          }`}
          onClick={() => setActiveTab("wingman")}
        >
          <span>✳</span> Wingman
        </button>

        <button
          className={`nav-item ${
            activeTab === "coach" ? "active" : ""
          }`}
          onClick={() => setActiveTab("coach")}
        >
          <span>◈</span> Coach
        </button>

        <button
          className={`nav-item ${
            activeTab === "voice" ? "active" : ""
          }`}
          onClick={() => setActiveTab("voice")}
        >
          <span>◉</span> Voice notes
        </button>

        <div className="sidebar-bottom">
          <div className="profile-avatar">S</div>
          <div>
            <strong>Your space</strong>
            <p>Personal account</p>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <span>YOUR CONVERSATION SPACE</span>

          <div className="status">
            <span className="status-dot"></span>
            Your personal wingman
          </div>
        </header>

        <section className="hero">
          <div className="eyebrow">
            A LITTLE HELP WITH WORDS
          </div>

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
                  ? "Share a message and we'll figure out a natural response."
                  : activeTab === "coach"
                  ? "Explore the context and understand how to respond."
                  : "Upload a voice note and let Prisma transcribe it."}
              </p>
            </div>

            <span className="sparkle">✳</span>
          </div>

          {/* Voice note upload */}
          {activeTab === "voice" && (
            <div className="composer">
              <label>UPLOAD YOUR VOICE NOTE</label>

              <input
                type="file"
                accept=".wav,.mp3,.ogg,.flac,.aac,.m4a,audio/*"
                onChange={(e) => {
                  setAudioFile(e.target.files?.[0] || null);
                  setTranscriptionStatus("");
                }}
              />

              {audioFile && (
                <p style={{ marginTop: "12px" }}>
                  Selected: {audioFile.name}
                </p>
              )}

              <button
                className="generate-button"
                onClick={transcribeAudio}
                disabled={!audioFile || transcribing}
                style={{ marginTop: "18px" }}
              >
                {transcribing
                  ? "Transcribing..."
                  : "◉ Transcribe voice note"}
                <span>↗</span>
              </button>

              {transcriptionStatus && (
                <p
                  style={{
                    marginTop: "14px",
                    fontSize: "14px",
                    lineHeight: "1.5"
                  }}
                  role="status"
                >
                  {transcriptionStatus}
                </p>
              )}
            </div>
          )}

          {/* Message composer */}
          <div className="composer">
            <label>
              {activeTab === "voice"
                ? "TRANSCRIBED MESSAGE"
                : "WHAT DID THEY SAY?"}
            </label>

            <textarea
              value={message}
              onChange={(e) => {
                setMessage(e.target.value);
                setReplies([]);
                setGenerationError("");
              }}
              placeholder={
                activeTab === "voice"
                  ? "Your transcription will appear here..."
                  : "Paste a message or conversation here..."
              }
            />

            <div className="composer-footer">
              <span>
                Only share conversations you have permission to use.
              </span>

              <span>{message.length} characters</span>
            </div>
          </div>

          {/* Tone selection */}
          <div className="tone-section">
            <label>HOW WOULD YOU LIKE TO RESPOND?</label>

            <div className="tone-options">
              {[
                "Natural",
                "Playful",
                "Thoughtful",
                "Flirty"
              ].map((item) => (
                <button
                  key={item}
                  className={`tone-button ${
                    tone === item ? "selected" : ""
                  }`}
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

          {/* Generate button */}
          <button
            className="generate-button"
            onClick={generateReplies}
            disabled={!message.trim() || generating}
          >
            {generating
              ? "Finding your words..."
              : "✳  Find my words"}
            <span>↗</span>
          </button>

          {/* Generation error */}
          {generationError && (
            <div
              role="alert"
              style={{
                marginTop: "18px",
                padding: "14px",
                borderRadius: "10px",
                background: "#fff0f0",
                color: "#b42318",
                fontSize: "14px",
                lineHeight: "1.5"
              }}
            >
              {generationError}
            </div>
          )}

          {/* Generated replies */}
          {replies.length > 0 && (
            <div
              style={{
                marginTop: "32px",
                display: "grid",
                gap: "16px"
              }}
            >
              <div>
                <h2>Your suggested replies.</h2>
                <p style={{ fontSize: "13px", color: "#777" }}>
                  Generated using {provider}.
                  Choose the one that sounds most like you.
                </p>
              </div>

              {replies.map((reply, index) => (
                <div
                  key={index}
                  style={{
                    padding: "20px",
                    border: "1px solid #e8e5e0",
                    borderRadius: "14px",
                    background: "#fff"
                  }}
                >
                  <div
                    style={{
                      fontSize: "12px",
                      color: "#888",
                      marginBottom: "10px",
                      letterSpacing: "1px"
                    }}
                  >
                    OPTION {index + 1}
                  </div>

                  <p
                    style={{
                      fontSize: "17px",
                      lineHeight: "1.6",
                      color: "#292929",
                      margin: "0 0 12px"
                    }}
                  >
                    {reply.text}
                  </p>

                  <p
                    style={{
                      fontSize: "13px",
                      color: "#888",
                      margin: "0 0 16px"
                    }}
                  >
                    {reply.explanation}
                  </p>

                  <button
                    onClick={() => copyReply(reply.text)}
                    style={{
                      padding: "9px 16px",
                      border: "1px solid #ddd",
                      borderRadius: "8px",
                      background: "#fff",
                      cursor: "pointer",
                      color: "#333"
                    }}
                  >
                    Copy reply
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="bottom-note">
            <span>✦</span>
            Your voice. Your choice. Always.
          </div>

          {/* Backend connection test */}
          <div
            style={{
              marginTop: "24px",
              textAlign: "center",
              padding: "15px"
            }}
          >
            <button
              onClick={testBackend}
              disabled={testing}
              style={{
                padding: "12px 24px",
                borderRadius: "10px",
                border: "1px solid #ddd",
                cursor: testing ? "wait" : "pointer",
                background: "#fff",
                color: "#333"
              }}
            >
              {testing
                ? "Testing connection..."
                : "Test Backend Connection"}
            </button>

            <p style={{ marginTop: "10px" }}>
              {connection}
            </p>
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
