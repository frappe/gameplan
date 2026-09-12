// Runs the full offline suite: US1-US6 (baseline offline UX) + P1-P3 (People/profile
// offline caching + background prefetch) + US7a/US7b (shared-computer cache scoping) +
// US8 (service worker update flow). Each story launches its own fresh browser/context
// for isolation. Run with: node tests/offline/runner.js (or `yarn test:offline` from
// frontend/).
const fs = require('fs')
const path = require('path')
const { RESULTS_DIR } = require('./config')

const stories = ['us1', 'us2', 'us3', 'us4', 'us5', 'us6', 'p1', 'p2', 'p3', 'us7a', 'us7b', 'us8']

async function main() {
  const summary = []
  for (const story of stories) {
    console.log(`\n=== Running ${story.toUpperCase()} ===`)
    const mod = require(`./${story}`)
    try {
      const r = await mod.run()
      summary.push({
        story: r.story,
        pass: r.pass,
        checks: (r.checks || []).map((c) => ({ name: c.name, pass: c.pass, symptom: c.symptom })),
        fatalError: r.fatalError,
        cleanup: r.cleanup,
      })
      console.log(`${story.toUpperCase()}: ${r.pass ? 'PASS' : 'FAIL'}`)
    } catch (e) {
      console.error(`${story.toUpperCase()} crashed:`, e)
      summary.push({ story: story.toUpperCase(), pass: false, fatalError: String(e) })
    }
  }

  fs.mkdirSync(RESULTS_DIR, { recursive: true })
  const outPath = path.join(RESULTS_DIR, 'summary.json')
  fs.writeFileSync(outPath, JSON.stringify(summary, null, 2))
  console.log('\n=== Summary ===')
  for (const s of summary) {
    console.log(`${s.story}: ${s.pass ? 'PASS' : 'FAIL'}`)
  }
  console.log(`\nFull summary written to ${outPath}`)

  if (summary.some((s) => !s.pass)) {
    process.exitCode = 1
  }
}

main()
