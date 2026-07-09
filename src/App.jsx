import { useState, useEffect } from "react";
import Papa from "papaparse";
import ExpressionAtlas from "./ExpressionAtlas";

export default function App() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/clean_table_mock.csv")
      .then((r) => r.text())
      .then((csv) => {
        const parsed = Papa.parse(csv, {
          header: true,
          dynamicTyping: true,
          skipEmptyLines: true,
        });
        setRows(parsed.data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to load data:", err);
        setLoading(false);
      });
  }, []);

  if (loading) return <p>Loading expression data…</p>;


  return (
    <div style={{ padding: "2rem", fontFamily: "system-ui, sans-serif" }}>
      <h1>Expression Atlas</h1>
      <p>Fold-change across salt level × timepoint</p>
      <ExpressionAtlas rows={rows} />
    </div>
  );
}