import { useCallback, useMemo, useState } from "react";

const languageMap = {
  en: "en-IN",
  hi: "hi-IN",
  mr: "mr-IN",
  ta: "ta-IN",
  kn: "kn-IN",
};

export function useVoiceInput({ language = "en", onResult } = {}) {
  const [listening, setListening] = useState(false);
  const supported = useMemo(() => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition), []);

  const start = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return false;

    const recognition = new SpeechRecognition();
    recognition.lang = languageMap[language] || languageMap.en;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognition.onresult = (event) => {
      const text = event.results?.[0]?.[0]?.transcript || "";
      if (text) onResult?.(text);
    };
    recognition.start();
    return true;
  }, [language, onResult]);

  return { listening, start, supported };
}
