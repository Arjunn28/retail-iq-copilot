import { useState, useEffect } from "react";

const suggestions = [
  "Top 5 products by sales",
  "Top categories by profit",
  "Lowest performing category by sales",
  "Top products in west in 2017 by sales",
  "Top products in east by profit",
  "Lowest products by profit",
  "Which category sales grew the fastest",
  "Which category profit declined the most"
];

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const [filteredSuggestions, setFilteredSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const [isBackendLive, setIsBackendLive] = useState(false);
  const [showPanel, setShowPanel] = useState(false);

  // Backend check
  const checkBackend = async () => {
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/ask?question=test`,
        {
          headers: {
            "ngrok-skip-browser-warning": "true"
          }
        }
      );
      setIsBackendLive(res.ok);
    } catch {
      setIsBackendLive(false);
    }
  };

  useEffect(() => {
    checkBackend();
  }, []);

  const handleChange = (e) => {
    const value = e.target.value;
    setQuery(value);

    if (value.length > 1) {
      const filtered = suggestions.filter((s) =>
        s.toLowerCase().includes(value.toLowerCase())
      );
      setFilteredSuggestions(filtered);
      setShowSuggestions(true);
    } else {
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setQuery(suggestion);
    setShowSuggestions(false);
  };

  const handleAsk = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setResponse(null);
    setShowSuggestions(false);

    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/ask?question=${encodeURIComponent(query)}`,
        {
          headers: {
            "ngrok-skip-browser-warning": "true"
          }
        }
      );

      const data = await res.json();
      setResponse(data);
    } catch {
      setResponse({
        insight: "⚠️ Backend is currently offline. Please try again later.",
        data: []
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white relative">

      {/* ☰ MENU BUTTON */}
      <button
        onClick={() => setShowPanel(true)}
        className="fixed top-5 left-5 text-2xl z-50 bg-white px-2 py-1 rounded shadow"
      >
        ☰
      </button>

      {/* OVERLAY */}
      {showPanel && (
        <div
          className="fixed inset-0 bg-black bg-opacity-30 z-40"
          onClick={() => setShowPanel(false)}
        />
      )}

      {/* LEFT PANEL (ALWAYS FIXED) */}
      <div
        className={`fixed top-0 left-0 h-full w-72 bg-white z-50 transform transition-transform duration-300 shadow-lg
        ${showPanel ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="p-6 text-sm text-gray-600 flex flex-col">

          {/* CLOSE */}
          <button
            onClick={() => setShowPanel(false)}
            className="text-xl self-end mb-4"
          >
            ✕
          </button>

          <h2 className="text-lg font-semibold text-black mb-4">
            Retail IQ Copilot
          </h2>

          <p className="mb-6">
            Ask questions about retail performance and get instant insights powered by SQL + AI.
          </p>

          <div className="mb-6">
            <h3 className="font-semibold text-black mb-2">Dataset</h3>
            <p>
              Orders, Products, Customers, Sales, Profit across regions and years.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-black mb-2">Try asking</h3>

            <ul className="space-y-2">
              {suggestions.map((q, i) => (
                <li
                  key={i}
                  onClick={() => {
                    handleSuggestionClick(q);
                    setShowPanel(false);
                    setTimeout(() => handleAsk(), 100);
                  }}
                  className="cursor-pointer hover:text-black hover:underline transition"
                >
                  • {q}
                </li>
              ))}
            </ul>
          </div>

        </div>
      </div>

      {/* MAIN CONTENT (PERFECT CENTER, NO SHIFT) */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">

        <h1 className="text-3xl font-bold">Retail IQ Copilot</h1>

        <p className={`text-sm ${isBackendLive ? "text-green-600" : "text-red-500"}`}>
          {isBackendLive ? "🟢 Backend Live" : "🔴 Backend Offline"}
        </p>

        <form
          className="flex flex-col items-center gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
        >
          <div className="relative w-96">
            <input
              type="text"
              placeholder="Ask a retail question..."
              value={query}
              onChange={handleChange}
              className="w-full p-3 rounded-lg border border-gray-300"
            />

            {showSuggestions && filteredSuggestions.length > 0 && (
              <ul className="absolute w-full bg-white border border-gray-200 rounded-lg mt-1 shadow z-10 max-h-60 overflow-y-auto">
                {filteredSuggestions.map((s, index) => (
                  <li
                    key={index}
                    onClick={() => handleSuggestionClick(s)}
                    className="p-2 cursor-pointer hover:bg-gray-100"
                  >
                    {s}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 bg-purple-600 text-white rounded-lg disabled:opacity-50"
          >
            Ask
          </button>
        </form>

        {/* RESULTS */}
        <div className="mt-24 w-full flex justify-center">
          <div className="w-96">

            {loading && (
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-purple-600"></div>
                <p className="text-gray-500 mt-2 text-sm">Thinking...</p>
              </div>
            )}

            {!loading && response && (
              <div className="p-4 bg-white rounded-lg shadow text-left">
                <p className="font-semibold mb-2">{response.insight}</p>

                {response.data && response.data.length > 0 && (
                  <table className="w-full text-sm border-collapse border border-gray-200">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 p-1">Name</th>
                        <th className="border border-gray-300 p-1">Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {response.data.map((item) => (
                        <tr key={item.name}>
                          <td className="border border-gray-300 p-1">{item.name}</td>
                          <td className="border border-gray-300 p-1">
                            {item.display_value || item.value}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}

          </div>
        </div>

      </div>

      {/* FOOTER */}
      <div className="footer fixed bottom-0 w-full text-center">
        <a
          href="https://github.com/Arjunn28/retail-iq-copilot"
          target="_blank"
          rel="noopener noreferrer"
          className="hover:text-gray-500 transition"
        >
          Built by Arjun · Data & AI · 2026
        </a>
      </div>

    </div>
  );
}

export default App;