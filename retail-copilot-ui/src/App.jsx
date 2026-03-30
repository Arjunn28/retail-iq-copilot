import { useState } from "react";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState(null);

  const handleAsk = async () => {
    console.log("Function running");
  
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/ask?question=${encodeURIComponent(query)}`
      );
  
      console.log("Status:", res.status);
  
      const data = await res.json();
      console.log("Data:", data);
  
      setResponse(data);
    } catch (error) {
      console.error("Error:", error);
    }
  };

  return (
    
    <div className="h-screen flex flex-col items-center justify-center bg-gray-100 gap-4">
      
      <h1 className="text-3xl font-bold">Retail IQ Copilot</h1>

      <input
        type="text"
        placeholder="Ask a retail question..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="w-96 p-3 rounded-lg border border-gray-300"
      />

    <button
      onClick={() => {
        console.log("Clicked");
        handleAsk();
      }}
      className="px-6 py-2 bg-purple-600 text-white rounded-lg"
    >
      Ask
    </button>

    {response && (
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
              {response.data.map((item, idx) => (
                <tr key={idx}>
                  <td className="border border-gray-300 p-1">{item.name}</td>
                  <td className="border border-gray-300 p-1">{item.display_value}</td>
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