export const languages = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "mr", label: "Marathi" },
  { code: "ta", label: "Tamil" },
  { code: "kn", label: "Kannada" },
];

export const assistantPrompts = {
  en: [
    "What should I do after tomato early blight?",
    "Suggest fertilizer for mango flowering",
    "How does rain affect coconut leaf rot?",
  ],
  hi: [
    "टमाटर अर्ली ब्लाइट के बाद क्या करें?",
    "आम के फूल आने पर कौन सा उर्वरक दें?",
    "बारिश से नारियल लीफ रॉट पर क्या असर होता है?",
  ],
  mr: [
    "टोमॅटो अर्ली ब्लाइट नंतर काय करावे?",
    "आंबा फुलोऱ्यासाठी खत सुचवा",
    "पावसामुळे नारळ लीफ रॉटवर काय परिणाम होतो?",
  ],
  ta: [
    "தக்காளி நோய்க்குப் பிறகு என்ன செய்ய வேண்டும்?",
    "மாம்பழ பூப்பதற்கு உரம் பரிந்துரைக்கவும்",
    "மழை தேங்காய் இலை அழுகலை எப்படி பாதிக்கும்?",
  ],
  kn: [
    "ಟೊಮೇಟೊ ರೋಗದ ನಂತರ ಏನು ಮಾಡಬೇಕು?",
    "ಮಾವಿನ ಹೂವಿಗೆ ಯಾವ ಗೊಬ್ಬರ?",
    "ಮಳೆ ತೆಂಗಿನ ಎಲೆ ರೋಗಕ್ಕೆ ಹೇಗೆ ಪರಿಣಾಮ ಬೀರುತ್ತದೆ?",
  ],
};

export function languageInstruction(language) {
  const labels = { hi: "Hindi", mr: "Marathi", ta: "Tamil", kn: "Kannada", en: "English" };
  return `Answer in ${labels[language] || "English"} when possible.`;
}
