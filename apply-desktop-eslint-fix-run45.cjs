"use strict";

const fs = require("node:fs");
const path = require("node:path");
const root = path.join(__dirname, "desktop-source");

function patch(relative, replacements) {
  const file = path.join(root, relative);
  if (!fs.existsSync(file)) throw new Error("Required desktop file is missing: " + relative);
  let source = fs.readFileSync(file, "utf8");
  for (const [before, after, label] of replacements) {
    const first = source.indexOf(before);
    if (first < 0 || first !== source.lastIndexOf(before)) {
      throw new Error("Expected " + label + " in " + relative + " was not found exactly once; refusing an unsafe patch.");
    }
    source = source.slice(0, first) + after + source.slice(first + before.length);
  }
  fs.writeFileSync(file, source, "utf8");
}

patch("app/admin/page.tsx", [[
"  useEffect(() => {\n    let active = true;\n    void loadWorkspace();\n    const authSubscription = supabase?.auth.onAuthStateChange(() => {",
"  useEffect(() => {\n    let active = true;\n    const initialLoad = window.setTimeout(() => { if (active) void loadWorkspace(); }, 0);\n    const authSubscription = supabase?.auth.onAuthStateChange(() => {",
"deferred admin workspace initial load"
],[
"    return () => {\n      active = false;\n      loadSequence.current += 1;",
"    return () => {\n      active = false;\n      window.clearTimeout(initialLoad);\n      loadSequence.current += 1;",
"admin initial-load timer cleanup"
]]);

patch("components/local-data-admin.tsx", [[
"  useEffect(() => { void refresh(); }, [refresh]);",
"  useEffect(() => {\n    const initialLoad = window.setTimeout(() => { void refresh(); }, 0);\n    return () => window.clearTimeout(initialLoad);\n  }, [refresh]);",
"deferred local data admin refresh"
]]);

patch("components/local-offline-workspace.tsx", [[
"  useEffect(() => { void loadSummary(); }, [loadSummary]);",
"  useEffect(() => {\n    const initialLoad = window.setTimeout(() => { void loadSummary(); }, 0);\n    return () => window.clearTimeout(initialLoad);\n  }, [loadSummary]);",
"deferred local offline summary load"
]]);

patch("app/page.tsx", [[
"  }, [globalQuery, catalogOnline]);",
"  }, [globalQuery, catalogOnline, query]);",
"keyboard handler query dependency"
]]);

patch("app/login/page.tsx", [[
'import { FormEvent, useMemo, useState } from "react";',
'import { FormEvent, useMemo, useState } from "react";\nimport { useRouter } from "next/navigation";',
"login router import"
],[
"export default function LoginPage(){\n const supabase=useMemo(()=>createClient(),[]);",
"export default function LoginPage(){\n const router = useRouter();\n const supabase=useMemo(()=>createClient(),[]);",
"login router initialization"
],[
'window.location.href="/";',
'router.replace("/");',
"internal login navigation"
]]);

patch("tests/local-core-db.test.cjs", [[
"  const now = new Date().toISOString();\n",
"",
"unused test timestamp"
]]);

console.log("Applied React lint fixes: deferred initial effects with cleanup, complete keyboard dependencies, router navigation, and unused test variable removal.");
