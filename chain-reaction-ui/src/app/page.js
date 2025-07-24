export default function Home() {
  return (
    <div>
      <h1 className="text-4xl font-bold mb-6">Welcome to Chain Reaction UI</h1>
      <p className="text-lg text-gray-600 mb-8">
        A user interface for interacting with the Chain Reaction API services.
      </p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl">
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h2 className="text-xl font-semibold mb-3">Translator</h2>
          <p className="text-gray-600 mb-4">
            Translate text into different languages using our AI-powered translation service.
          </p>
          <a
            href="/translator"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Translator →
          </a>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
          <h2 className="text-xl font-semibold mb-3">Translator Chain</h2>
          <p className="text-gray-600 mb-4">
            Chain multiple translations together to see how text transforms through different languages.
          </p>
          <a
            href="/translator-chain"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Try Chain →
          </a>
        </div>
      </div>
      
      <div className="mt-12 p-6 bg-gray-50 rounded-lg">
        <h3 className="text-lg font-semibold mb-2">API Status</h3>
        <p className="text-gray-600">
          Make sure the Chain Reaction API is running at{' '}
          <code className="bg-gray-200 px-2 py-1 rounded">http://localhost:8000</code>
        </p>
      </div>
    </div>
  );
}