import React, { useRef } from "react";
import "./CodeEditor.css"
import Editor from "@monaco-editor/react";

const CodeEditor = ({ code, onChange, isMobile }) => {
  const editorRef = useRef(null);

  const handleEditorChange = (value) => {
    onChange(value);
  };

  const editorOptions = {
    className: 'code-editor',
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    fontSize: isMobile? 14: 17,
    lineNumbersMinChars: isMobile? 3: 5,
    folding: isMobile? false: true
  };

  return (
      <Editor
        height="63vh"
        width={`100%`}
        language={"c"}
        value={code}
        onChange={handleEditorChange}
        options={editorOptions}
        editorDidMount={(editor, monaco) => {
          editorRef.current = editor;
        }}
      />
  );
};

export default CodeEditor;