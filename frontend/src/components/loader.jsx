import React from "react";
import "./loader.css";

function Loader() {
  return (
    <div className="loader">
      <div className="spinner"></div>
      <p>Analyzing SEO data... ⏳</p>
    </div>
  );
}

export default Loader;
