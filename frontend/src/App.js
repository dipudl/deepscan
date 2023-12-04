import React, { useState, useEffect } from 'react';
import CodeEditor from "./CodeEditor";
import axios from 'axios';

import { defaultCode } from './utils';
import './App.css';

const baseUrl = "http://localhost:8000";

function App() {

  const [inputCode, setInputCode] = useState(defaultCode)
  const [output, setOutput] = useState({})
  const [analyzing, setAnalyzing] = useState(false)
  const [emptyResult, setEmptyResult] = useState(false)
  const [showOutput, setShowOutput] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 800px)");
    setIsMobile(mediaQuery.matches);

    const handleMediaQueryChange = (event) => {
      setIsMobile(event.matches);
    };

    mediaQuery.addEventListener("change", handleMediaQueryChange);

    return () => {
      mediaQuery.removeEventListener("change", handleMediaQueryChange);
    };
  }, []);

  useEffect(() => {
    const element = document.getElementById("output");
    isMobile && element.scrollIntoView({ behavior: 'smooth' });
  }, [output]);

  const analyzeCode = async () => {
    setAnalyzing(true);

    axios.post(`${baseUrl}/analyze`, {
        "code": inputCode
      }, {
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        },
      })
      .then((response) => {
        console.log(response.data.replace(/'/ig,'"'));
        const result = JSON.parse(response.data.replace(/'/ig,'"')).analysis;

        if(result["function_args_swap_bug"].length === 0 && result["wrong_binary_operator_bug"].length === 0) {
          setEmptyResult(true);
        } else {
          setEmptyResult(false);
        }

        setOutput(result);
        setShowOutput(true);
      })
      .catch(error => {
        alert(error.message);
      })
      .finally(() => {
        setAnalyzing(false);
      })
  }

  return (
    <div className="App">
      <nav className="App-Navbar">
        <h1 className="App-Navbar-title">DeepScan</h1>
      </nav>
      <section className="App-code-analysis-section">
        <div className="App-code-input-div">
          <h2 className="App-code-input-title">Write your code here</h2>
          <div className="App-code-editor-div">
            {/* <textarea
                name="input-code"
                type="text"
                id="input-code"
                rows="22"
                value={inputCode}
                onChange={(e) => setInputCode(e.target.value)}
                required
            /> */}
 
            <CodeEditor
              code={inputCode}
              onChange={(value) => setInputCode(value)}
              isMobile={isMobile}
            />
          </div>

            <button
              className="App-code-input-analyze-button"
              type='submit'
              onClick={() => analyzeCode()}
            >
              {analyzing? "Analyzing...": "Analyze"}
            </button>
        </div>
        {showOutput &&
        <div className="App-code-output-div" id="output">
          <h2 className="App-code-output-title">Output description</h2>
          <div className="App-code-output">
            <div className="App-code-output-text">
              {!emptyResult
              ? Object.keys(output).length !== 0 && <>
                <ul>{output["function_args_swap_bug"].map((e, index) =>
                  <li key={index}>{`${e.function_name}: ${(e.probability * 100).toFixed(2)}% ${e.label === 1? "buggy": "correct"} [line ${e.start_line}, cloumn ${e.start_column} to line ${e.end_line}, column ${e.end_column}]`}</li>
                )}</ul>

                {output["function_args_swap_bug"].length !==0 && output["wrong_binary_operator_bug"].length !== 0 && <hr/>}

                <ul>{output["wrong_binary_operator_bug"].map((e, index) =>
                  <li key={index}>{`${e.operator} : ${(e.probability * 100).toFixed(2)}% ${e.label === 1? "buggy": "correct"} [line ${e.start_line}, cloumn ${e.start_column} to line ${e.end_line}, column ${e.end_column}]`}</li>
                )}</ul>
              </>
              : "No bugs found!"}
            </div>
          </div>
        </div>
        }
      </section>
    </div>
  );
}

export default App;