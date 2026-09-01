const [major] = process.versions.node.split(".").map(Number);
if (major < 20) {
  console.error(`Node.js 20 or newer is required; found ${process.versions.node}`);
  process.exitCode = 1;
} else {
  console.log(JSON.stringify({ node: process.versions.node, runtime_preflight: "ok" }));
}
