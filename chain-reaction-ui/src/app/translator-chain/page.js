'use client';

import { useState } from 'react';

export default function TranslatorChainPage() {
  const [text, setText] = useState('');
  const [languages, setLanguages] = useState(['Telugu', 'Hindi', 'English']);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const availableLanguages = ['Telugu', 'Hindi', 'Spanish', 'French', 'German', 'Italian', 'Portuguese', 'Dutch', 'Russian', 'Japanese', 'Korean', 'Chinese', 'English'];

  const handleAddLanguage = () => {
    if (languages.length < 5) {
      setLanguages([...languages, 'English']);
    }
  };

  const handleRemoveLanguage = (index) => {
    if (languages.length > 2) {
      setLanguages(languages.filter((_, i) => i !== index));
    }
  };

  const handleLanguageChange = (index, value) => {
    const newLanguages = [...languages];
    newLanguages[index] = value;
    setLanguages(newLanguages);
  };

  const handleTranslate = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/chain/samples/translate-chain', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text: text,
          languages: languages
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
      <h1 className="text-3xl font-bold mb-6">Translator Chain</h1>
      <p className="text-gray-600 mb-8">Chain multiple translations through different languages</p>

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
          <div className="flex justify-between items-center mb-3">
            <label className="block text-sm font-medium text-gray-700">
              Translation Chain
            </label>
            <button
              onClick={handleAddLanguage}
              disabled={languages.length >= 5}
              className={`px-4 py-2 text-sm rounded-lg font-medium transition-colors ${
                languages.length >= 5
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-green-600 text-white hover:bg-green-700'
              }`}
            >
              Add Language
            </button>
          </div>

          <div className="space-y-3">
            {languages.map((lang, index) => (
              <div key={index} className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-500 w-20">
                  Step {index + 1}:
                </span>
                <select
                  value={lang}
                  onChange={(e) => handleLanguageChange(index, e.target.value)}
                  className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {availableLanguages.map((availableLang) => (
                    <option key={availableLang} value={availableLang}>
                      {availableLang}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => handleRemoveLanguage(index)}
                  disabled={languages.length <= 2}
                  className={`px-3 py-2 text-sm rounded-lg font-medium transition-colors ${
                    languages.length <= 2
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-red-600 text-white hover:bg-red-700'
                  }`}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Text will be translated through each language in sequence
          </p>
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
          {loading ? 'Translating...' : 'Translate Chain'}
        </button>

        {result && (
          <div className="mt-8 p-6 bg-gray-50 rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Translation Chain Result</h2>
            <div className="space-y-4">
                <div className="mt-2 space-y-2">
                  {result.results && Object.keys(result.results).map((key, index) => (
                    <div key={index} className="pl-4 border-l-2 border-blue-300">
                      <p className="text-sm text-gray-600">
                        Step {index + 1}
                      </p>
                      <p className="text-gray-900">{result.results[key]}</p>
                      <p className="text-gray-900">{key}</p>
                    </div>
                  ))}
                </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}