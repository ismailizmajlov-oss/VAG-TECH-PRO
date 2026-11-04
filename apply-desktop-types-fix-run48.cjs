"use strict";
const fs = require("node:fs");
const path = require("node:path");
const root = path.join(__dirname, "desktop-source");

function replaceDbRowDeclaration(source) {
  const typeStart = source.indexOf("type DbRow");
  const interfaceStart = source.indexOf("interface DbRow");
  const start = typeStart >= 0 ? typeStart : interfaceStart;
  if (start < 0) throw new Error("DbRow declaration was not found in app/page.tsx");
  if (typeStart >= 0) {
    const equals = source.indexOf("=", typeStart);
    if (equals < 0) throw new Error("DbRow type alias has no equals sign");
    let cursor = equals + 1;
    while (/\s/.test(source[cursor] || "")) cursor++;
    let end;
    if (source[cursor] === "{") {
      let depth = 0;
      for (let i = cursor; i < source.length; i++) {
        if (source[i] === "{") depth++;
        else if (source[i] === "}") {
          depth--;
          if (depth === 0) { end = i + 1; if (source[end] === ";") end++; break; }
        }
      }
      if (!end) throw new Error("Could not find the end of the DbRow object type");
    } else {
      const semi = source.indexOf(";", cursor);
      if (semi < 0) throw new Error("Could not find the end of the DbRow type alias");
      end = semi + 1;
    }
    const existing = source.slice(start, end);
    if (existing.includes("Record<string, any>")) return source;
    return source.slice(0, start) + "type DbRow = Record<string, any>;" + source.slice(end);
  }
  const brace = source.indexOf("{", interfaceStart);
  if (brace < 0) throw new Error("DbRow interface has no opening brace");
  let depth = 0, end;
  for (let i = brace; i < source.length; i++) {
    if (source[i] === "{") depth++;
    else if (source[i] === "}") { depth--; if (depth === 0) { end = i + 1; break; } }
  }
  if (!end) throw new Error("Could not find the end of the DbRow interface");
  return source.slice(0, interfaceStart) + "type DbRow = Record<string, any>;" + source.slice(end);
}

const pageFile = path.join(root, "app", "page.tsx");
if (!fs.existsSync(pageFile)) throw new Error("app/page.tsx is missing");
let page = fs.readFileSync(pageFile, "utf8");
page = replaceDbRowDeclaration(page);
fs.writeFileSync(pageFile, page, "utf8");

const researchFile = path.join(root, "components", "local-research-catalog.tsx");
if (!fs.existsSync(researchFile)) throw new Error("components/local-research-catalog.tsx is missing");
let research = fs.readFileSync(researchFile, "utf8");
research = research.replaceAll("row.affectedComponents", "(row.affectedComponents ?? [])");
research = research.replaceAll("row.commonCauses", "(row.commonCauses ?? [])");
fs.writeFileSync(researchFile, research, "utf8");
console.log("Applied explicit dynamic Supabase row typing and safe empty-array defaults for optional research metadata.");
