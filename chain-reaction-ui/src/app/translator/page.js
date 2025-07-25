'use client';

import { useState } from 'react';
import Select from '@/components/Select';
import Button from '@/components/Button';

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
      <h1 className="text-3xl font-bold mb-1">Translator</h1>
      <p className="text-gray-600 mb-8">Translate text to different languages using the Chain Reaction API</p>

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
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target Language
          </label>
          <Select
            value={language}
            onChange={setLanguage}
            options={languages}
            placeholder="Select a language"
          />
        </div>

        <Button
          onClick={handleTranslate}
          disabled={!text}
          loading={loading}
          size="small"
        >
          Translate
        </Button>

        {result && (
          <div className="mt-8 p-6 bg-gray-50 rounded-lg">
            <div className="space-y-3">
              <div>
                <p className="mt-1 text-gray-900">{result.text}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}