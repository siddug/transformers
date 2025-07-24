'use client';

import { useState } from 'react';

export default function TranslatorPage() {
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('Telugu');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const languages = ['Telugu', 'Hindi', 'Spanish', 'French', 'German', 'Italian', 'Portuguese', 'Dutch', 'Russian', 'Japanese', 'Korean', 'Chinese'];

  const handleTranslate = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/chain/samples/translate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          languages: [language]
        }),
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Translation error:', error);
      alert('Failed to translate. Please make sure the API is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Translator</h1>
      <p className="text-gray-600 mb-8">Translate text to different languages using the Chain Reaction API</p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Text to translate
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows="4"
            placeholder="Enter text to translate..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target Language
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            {languages.map((lang) => (
              <option key={lang} value={lang}>
                {lang}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleTranslate}
          disabled={!text || loading}
          className={`px-6 py-3 rounded-lg font-medium text-white transition-colors ${
            loading || !text
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? 'Translating...' : 'Translate'}
        </button>

        {result && (
          <div className="mt-8 p-6 bg-gray-50 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Translation Result</h2>
            <div className="space-y-3">
              <div>
                <span className="font-medium text-gray-700">Original:</span>
                <p className="mt-1 text-gray-900">{result.text}</p>
              </div>
              <div>
                <span className="font-medium text-gray-700">Translation:</span>
                <p className="mt-1 text-gray-900">{result.translated_text}</p>
              </div>
              <div>
                <span className="font-medium text-gray-700">Language:</span>
                <p className="mt-1 text-gray-900">{result.language}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}