'use client';

import { useState } from 'react';
import Select from '@/components/Select';
import Button from '@/components/Button';

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
      <h1 className="text-3xl font-bold mb-1">Translator Chain</h1>
      <p className="text-gray-600 mb-8">Chain multiple translations through different languages</p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Text to translate
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded focus:outline-none"
            rows="4"
            placeholder="Enter text to translate..."
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-3">
            <label className="block text-sm font-medium text-gray-700">
              Translation Chain
            </label>
            <Button
              onClick={handleAddLanguage}
              disabled={languages.length >= 5}
              size="small"
              variant="secondary"
            >
              Add Language
            </Button>
          </div>

          <div className="space-y-3">
            {languages.map((lang, index) => (
              <div key={index} className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-500 w-20">
                  Step {index + 1}:
                </span>
                <div className="flex-1">
                  <Select
                    value={lang}
                    onChange={(value) => handleLanguageChange(index, value)}
                    options={availableLanguages}
                    placeholder="Select a language"
                  />
                </div>
                <Button
                  onClick={() => handleRemoveLanguage(index)}
                  disabled={languages.length <= 2}
                  size="small"
                  variant="danger"
                >
                  Remove
                </Button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Text will be translated through each language in sequence
          </p>
        </div>

        <Button
          onClick={handleTranslate}
          disabled={!text}
          loading={loading}
          size="small"
        >
          Translate Chain
        </Button>

        {result && (
          <div className="mt-8 p-6 bg-gray-50 rounded-lg">
            <div className="space-y-4">
                <div className="mt-2 space-y-4">
                  {result.results && Object.keys(result.results).map((key, index) => (
                    <div key={index} className="pl-4 border-l-2 border-blue-300">
                      <p className="text-xs text-gray-600">
                        Step {index + 1} - {key}
                      </p>
                      <p className="text-gray-900 mt-1">{result.results[key]}</p>
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