import { useState, useRef, useEffect } from 'react';
import './App.css';

// Fix viewport height for mobile browsers with keyboard
function setViewportHeight() {
  const viewportHeight = window.visualViewport?.height || window.innerHeight;
  document.documentElement.style.setProperty('--vh', `${viewportHeight}px`);
}

function App() {
  useEffect(() => {
    setViewportHeight();
    window.addEventListener('resize', setViewportHeight);
    return () => {
      window.removeEventListener('resize', setViewportHeight);
    };
  }, []);

  // Set states
  const [prompt, setWord] = useState<string>('');
  const [messages, setMessages] = useState<{ role: string; content: { message: string, wikiData: any}; id: number }[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('gemini_mcp');

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputBarRef = useRef<HTMLDivElement | null>(null);

  // Scroll to the bottom of the messages when new messages are added
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Sending Prompts & receiving the server's responses
  const sendPrompt = async () => {
    if (!prompt.trim()) return; // No empty messages
    setWord(''); // Clear the input field
    setMessages((prev) => [...prev, { role: 'user', content: { message: prompt, wikiData:null }, id: Date.now() }]); // Add User prompt to the chat

    // Add a placeholder for the server response
    const loadingMessageId = Date.now(); // Unique ID for the loading message
    setMessages((prev) => [
      ...prev,
      { role: 'server', content: { message: 'Loading Response...', wikiData: null }, id: loadingMessageId },
    ]);

    // Fetch the server response
    try {
      const encodedPrompt = encodeURIComponent(prompt); // avoid problems with characters like #, ?, etc.
      // const backendUrl = "http://localhost:5000"
      const backendUrl = "https://api.wikiquery.org";
      const response = await fetch(`${backendUrl}/userInput?prompt=${encodedPrompt}&model=${selectedModel}`);
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      const responseData = await response.json();

      // Replace the loading message with the actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingMessageId && msg.role === 'server' ? { ...msg, content: {message: responseData.message, wikiData: (responseData.query && 'Fetching Wikidata...') } } : msg // Determine if the response has a query and set wikiData accordingly
      ));

      // Fetch the Wikidata results (if query exists)
      if (responseData.query) {
        try {
          const queryResult = await fetch('https://query.wikidata.org/sparql', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
              'Accept': 'application/json',
            },
            body: new URLSearchParams({ query: responseData.query }),
          });

          if (!queryResult.ok) {
            throw new Error(`Wikidata error: ${queryResult.status}`);
          }

          // Update the message with the Wikidata result
          const wikiData = await queryResult.json();
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === loadingMessageId && msg.role === 'server' 
                ? { ...msg, content: { ...responseData, wikiData: wikiData } }
                : msg
            )
          );
          // Handle Wikidata errors
        } catch (error) {
          console.error('Error fetching Wikidata:', error);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === loadingMessageId && msg.role === 'server' 
                ? { ...msg, content: { ...responseData, wikiData: 'Oops, that query seems to be malformed!' } }
                : msg
            )
          );
        }
      }
      // Handle server errors
    } catch (error) {
      console.error('Error:', error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingMessageId && msg.role === 'server' 
            ? {
                ...msg,
                content: { message: (error instanceof Error && 
                  error.message.includes('400') ? `Bad Request: ${selectedModel} might not exist or ${prompt} might not be valid` 
                  : 'Error: Backend server could not be reached or delivered an invalid result.'), wikiData: null },
              } : msg
        )
      );
    }
  };

  // HTML page
  return (
    <div className="app-container">
      <header className="header">
        <h1>Wikiquery</h1>
        <div className="account-icon"></div>
      </header>

      <div className="message-interface">
        {messages.map((msg, index) => (
          <div key={index} className={`message-row ${msg.role}`}>
            <div className={`message-bubble ${msg.role} hide-scrollbar`}>
              {/* Render Message */}
              {msg.content.message && (
                typeof msg.content.message === 'string' ? (
                  parseSparqlText(msg.content.message)
                ) : (
                  JSON.stringify(msg.content, null, 2)
                )
              )}
              {/* Break before displaying table */}
              {msg.content.wikiData && msg.content.message && <br />}
              {msg.content.wikiData && msg.content.message && <br />}
              {/* Render wikiData result as String for "Fetching..", "Error" etc, JSON as backup if query has wrong format */}
              {msg.content.wikiData && typeof msg.content.wikiData === 'string' && String(msg.content.wikiData)}
              {msg.content.wikiData && !(typeof msg.content.wikiData === 'string') && !(msg.content.wikiData.head && msg.content.wikiData.results) && JSON.stringify(msg.content.wikiData, null, 2)}
              {/* {JSON.stringify(msg.content.wikiData, null, 2)} */}
              {/* Render wikiData as table */}
              {msg.content.wikiData && msg.content.wikiData.head && msg.content.wikiData.results && renderWikiDataTable(msg.content.wikiData)}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div ref={inputBarRef} className="input-bar">
        <input
          className="prompt-input"
          type="text"
          value={prompt}
          onChange={(e) => setWord(e.target.value)}
          onKeyDown={(e) => {
            setViewportHeight();
            if (e.key === 'Enter') {
              sendPrompt();
            }
          }}
          placeholder="Ask Wikiquery..."
        />
        <div className='input-actions'>
          <select
            className="model-dropdown"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            <option value="gemini_mcp">Gemini MCP</option>
            <option value="gemini">Gemini 2.5 flash</option>
            <option value="gemini_finetune">Gemini (finetuned)</option>
            <option value="gemini_finetune_mcp">MCP (finetuned)</option>
            <option value="test">Test</option>
          </select>
          <button onClick={sendPrompt} className="send-button">
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

// Rendering the message text (with code styling)
const parseSparqlText = (text: string) => {  
  const regex = /```sparql\n([\s\S]*?)```/g; // between "```sparql\n" and "```""
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    // Add text before the match
    if (match.index > lastIndex) {
      parts.push(
        text
          .slice(lastIndex, match.index)
          .split('\n')
          .map((line, index, array) => (
            <span key={`text-${lastIndex + index}`}>
              {line}
              {index < array.length - 1 && <br />} {/* Add <br /> between lines */}
            </span>
          ))
      );
    }
    // Add Code text
    parts.push(
      <code key={match.index}>
        {match[1].split('\n').map((line, index, array) => {
          const commentIndex = line.indexOf('#');
          return (
            <span key={index}>
              {commentIndex === -1 ? (
                line
              ) : (
                <>
                  {line.slice(0, commentIndex)}
                  <span className='comment'>
                    {line.slice(commentIndex)}
                  </span>
                </>
              )}
              {index < array.length - 1 && <br />} {/* Add <br /> between lines */}
            </span>
          );
        })}
      </code>
    );
    lastIndex = regex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(
      text
        .slice(lastIndex)
        .split('\n')
        .map((line, index, array) => (
          <span key={`text-${lastIndex + index}`}>
            {line}
            {index < array.length - 1 && <br />} {/* Add <br /> between lines */}
          </span>
        ))
    );
  }
  return parts.flat();
};

// Rendering the table
interface WikiData {
  head: {
    vars: string[];
  };
  results: {
    bindings: Array<{
      [key: string]: {
        type: string;
        value: string;
      };
    }>;
  };
}

const renderWikiDataTable = (wikiData: WikiData) => {
  const { vars } = wikiData.head;
  const { bindings } = wikiData.results;
  return (
    <table className="wiki-result-table">
      <thead>
        <tr>
          {vars.map((varName) => (
            <th key={varName}>{varName}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {bindings.map((binding, index) => (
          <tr key={index}>
            {vars.map((varName) => (
              <td key={varName}>
                {binding[varName]?.type === 'uri' ? (
                  <a href={binding[varName].value} target="_blank" rel="noopener noreferrer">
                    {binding[varName].value}
                  </a>
                ) : (
                  binding[varName]?.value || ''
                )}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default App;


// TODO:


// Feature idea: Add option to render SPARQL queries with P: and Q: replaced with the actual labels