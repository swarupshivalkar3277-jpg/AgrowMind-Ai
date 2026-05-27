import { useState } from "react";
import { Bot, Leaf, Mic, Send, Sparkles } from "lucide-react";
import toast from "react-hot-toast";

import { askAssistant } from "../services/authService";
import { useVoiceInput } from "../hooks/useVoiceInput";
import { assistantPrompts, languageInstruction, languages } from "../utils/i18n";

const initialMessages = [
  {
    role: "assistant",
    text: "Hello. I can help with disease advice, crop care, fertilizer suggestions, weather actions, and marketplace recommendations.",
  },
];

function errorMessage(error) {
  const detail = error?.response?.data?.error || error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail?.detail) return detail.detail;
  return error?.message || "Assistant request failed";
}

export default function AssistantPage() {
  const [messages, setMessages] = useState(initialMessages);
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [language, setLanguage] = useState("en");
  const prompts = [...(assistantPrompts[language] || assistantPrompts.en), "Which products match my last diagnosis?"];
  const voice = useVoiceInput({ language, onResult: setQuestion });

  async function sendMessage(text = question) {
    const clean = text.trim();
    if (!clean || sending) return;

    setMessages((current) => [...current, { role: "user", text: clean }]);
    setQuestion("");
    setSending(true);
    try {
      const { data } = await askAssistant({ question: `${clean}\n\n${languageInstruction(language)}` });
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: data.answer || "I could not generate an answer for that question.",
          sources: data.sources || [],
          products: data.recommended_products || [],
          provider: data.provider,
        },
      ]);
    } catch (error) {
      const message = errorMessage(error);
      toast.error(message);
      setMessages((current) => [...current, { role: "assistant", text: message }]);
    } finally {
      setSending(false);
    }
  }

  function submit(event) {
    event.preventDefault();
    sendMessage();
  }

  return (
    <main className="pageStack assistantPage">
      <section className="pageHero compactHero">
        <div>
          <span className="eyebrowText">AI Farming Assistant</span>
          <h1>Ask practical farming questions.</h1>
          <p>Conversation history, disease advice, fertilizer guidance, crop recommendations, and weather-aware support.</p>
        </div>
      </section>
      <section className="assistantLayout">
        <aside className="panel assistantSidebar">
          <h2>Suggested questions</h2>
          <label className="languagePicker"><span>Language</span><select onChange={(event) => setLanguage(event.target.value)} value={language}>{languages.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select></label>
          {prompts.map((prompt) => (
            <button className="secondaryButton" disabled={sending} key={prompt} onClick={() => sendMessage(prompt)} type="button">
              <Sparkles size={16} /> {prompt}
            </button>
          ))}
        </aside>
        <section className="panel chatPanel">
          <div className="chatMessages">
            {messages.map((message, index) => (
              <article className={message.role === "user" ? "userBubble" : "assistantBubble"} key={`${message.role}-${index}`}>
                {message.role === "user" ? <Leaf size={20} /> : <Bot size={20} />}
                <div>
                  <p>{message.text}</p>
                  {message.provider && <small>Provider: {message.provider}</small>}
                  {message.sources?.length > 0 && <small>{message.sources.length} source(s) used</small>}
                </div>
              </article>
            ))}
            {sending && <article className="assistantBubble"><Bot size={20} /><p className="typingDots"><span /> <span /> <span /></p></article>}
          </div>
          <form className="chatInput" onSubmit={submit}>
            <input disabled={sending} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask AgroMind AI..." value={question} />
            <button aria-label="Voice assistant" className={voice.listening ? "listening" : ""} disabled={sending || !voice.supported} onClick={voice.start} type="button"><Mic size={18} /></button>
            <button aria-label="Send message" disabled={sending || !question.trim()} type="submit"><Send size={18} /></button>
          </form>
        </section>
      </section>
    </main>
  );
}
