import { useState } from "react";

const suggestions = [
  // SALES
  "Top 5 products by sales",
  "Top 10 products by sales",
  "Bottom 5 products by sales",
  "Lowest selling products",
  "Highest selling products",
  "Products with highest sales in 2017",
  "Top products in west in 2017",
  "Top products in east",
  "Best performing products",

  // CATEGORY
  "Top 3 categories by profit",
  "Best category in central region",
  "Top categories in east in 2016 by profit",
  "Highest revenue category",
  "Least performing category",
  "Which category has lowest sales",

  // PROFIT
  "Top products by profit",
  "Least profitable products",
  "Highest profit categories",
  "Products with negative profit",

  // GROWTH / DECLINE
  "Which category grew the fastest in 2017",
  "Which category declined the most in 2016",
  "Highest growth category",
  "Categories with maximum growth",
  "Which category had the biggest increase in sales",
  "Which category had the biggest drop in sales",
  "Top growing categories",
  "Least growing categories",

  // REGIONAL
  "Top products in west region",
  "Top categories in south",
  "Best products in east region",

  // MIXED
  "Top 5 products in west in 2017 by sales",
  "Bottom 3 categories by profit in 2016",
  "Highest growth products in 2017"
];

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const [filteredSuggestions, setFilteredSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // INPUT HANDLER
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

  // CLICK SUGGESTION
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

      //   const res = await fetch(
      //   `http://127.0.0.1:8000/ask?question=${encodeURIComponent(query)}`
      // );
      
      //   const res = await fetch(
      //   `https://growable-augusta-ivied.ngrok-free.dev/ask?question=${encodeURIComponent(query)}`,
      //   {
      //     headers: {
      //       "ngrok-skip-browser-warning": "true"
      //     }
      //   }
      // );

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
    } catch (error) {
      console.error("Error:", error);
    }

    setLoading(false);
  };

  return (
    <div className="h-screen flex flex-col items-center justify-center bg-gray-100 gap-4">
      <h1 className="text-3xl font-bold">Retail IQ Copilot</h1>

      {/* FORM WRAP (FIXES ENTER KEY) */}
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

      {/* LOADING */}
      {loading && (
        <div className="flex flex-col items-center mt-4">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-purple-600"></div>
          <p className="text-gray-500 mt-2 text-sm">Thinking...</p>
        </div>
      )}

      {/* RESPONSE */}
      {!loading && response && (
        <div className="mt-4 p-4 bg-white rounded-lg shadow w-96 text-left">
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
  );
}

export default App;