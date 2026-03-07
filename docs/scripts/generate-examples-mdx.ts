/**
 * Generates static .mdx files from example .py files for devportal inclusion.
 *
 * Reuses parsing helpers from the examples-loader.
 * Output goes to src/content/docs/examples/ so it gets packaged in the tarball.
 *
 * Run: npx tsx docs/scripts/generate-examples-mdx.ts
 */

import fs from 'node:fs'
import path from 'node:path'
import { parseDocstring, extractOrder, createSlug, lineSeparator } from '../src/loaders/examples-loader.ts'

const REPO_ROOT = path.resolve(import.meta.dirname, '..', '..')
const EXAMPLES_DIR = path.join(REPO_ROOT, 'examples', 'subscriber')
const OUTPUT_DIR = path.join(REPO_ROOT, 'docs', 'src', 'content', 'docs', 'examples')
const GITHUB_BASE = 'https://github.com/algorandfoundation/algokit-subscriber-py/blob/main/examples/subscriber'

// Clean output directory
if (fs.existsSync(OUTPUT_DIR)) {
  fs.rmSync(OUTPUT_DIR, { recursive: true })
}
fs.mkdirSync(OUTPUT_DIR, { recursive: true })

// Collect all examples
type ExampleInfo = { title: string; slug: string; description: string; filename: string; order: number }
const allExamples: ExampleInfo[] = []

const files = fs.readdirSync(EXAMPLES_DIR).filter((f) => f.endsWith('.py') && !f.startsWith('_'))

for (const filename of files) {
  const content = fs.readFileSync(path.join(EXAMPLES_DIR, filename), 'utf-8')
  const { title, description, prerequisites } = parseDocstring(content)
  const order = extractOrder(filename)
  const slug = createSlug(filename)
  const githubUrl = `${GITHUB_BASE}/${filename}`
  const runCommand = `uv run python ${filename}`

  const prereqText = prerequisites || 'LocalNet running (`algokit localnet start`)'

  allExamples.push({ title, slug, description, filename, order })

  const mdx = `---
title: "${title}"
description: "${description.split('\n')[0].replace(/"/g, '\\"')}"
sidebar:
  order: ${order}
---

[← Back to Examples](../)

## Description

${description.replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\{/g, '&#123;').replace(/\}/g, '&#125;')}

## Prerequisites

${prereqText}

## Run This Example

From the repository's \`examples/subscriber\` directory:

\`\`\`bash
cd examples/subscriber
${runCommand}
\`\`\`

## Code

[View source on GitHub](${githubUrl})

\`\`\`python title="${filename}"
${content}
\`\`\`

---

### Other examples

PLACEHOLDER_OTHER_EXAMPLES
`

  fs.writeFileSync(path.join(OUTPUT_DIR, `${slug}.mdx`), mdx)
}

// Sort examples by order
allExamples.sort((a, b) => a.order - b.order)

// Second pass: replace placeholder with actual sibling links
for (const example of allExamples) {
  const filePath = path.join(OUTPUT_DIR, `${example.slug}.mdx`)
  let content = fs.readFileSync(filePath, 'utf-8')

  const siblingLinks = allExamples
    .map((ex) => (ex.slug === example.slug ? `- **${ex.title}**` : `- [${ex.title}](../${ex.slug}/)`))
    .join('\n')

  content = content.replace('PLACEHOLDER_OTHER_EXAMPLES', siblingLinks)
  fs.writeFileSync(filePath, content)
}

// Generate index.mdx with HTML table
const escapeForMdx = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\{/g, '&#123;').replace(/\}/g, '&#125;')

const tableRows = allExamples
  .map((ex) => {
    const lines = ex.description.split('\n')
    let descHtml = ''
    let bulletBuffer: string[] = []
    const flushBullets = () => {
      if (bulletBuffer.length > 0) {
        descHtml += '<ul>' + bulletBuffer.map((b) => `<li>${escapeForMdx(b)}</li>`).join('') + '</ul>'
        bulletBuffer = []
      }
    }
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      if (/^[-•]\s/.test(trimmed)) {
        bulletBuffer.push(trimmed.replace(/^[-•]\s*/, ''))
      } else {
        flushBullets()
        descHtml += `<p>${escapeForMdx(trimmed)}</p>`
      }
    }
    flushBullets()

    return `<tr><td><a href="${ex.slug}/">${escapeForMdx(ex.title)}</a></td><td>${descHtml}</td></tr>`
  })
  .join('\n')

fs.writeFileSync(
  path.join(OUTPUT_DIR, 'index.mdx'),
  `---
title: Code Examples
description: "${allExamples.length} runnable Python examples demonstrating AlgoKit Subscriber features"
sidebar:
  order: 0
---

Browse **${allExamples.length}** runnable Python examples demonstrating AlgoKit Subscriber features. Each example is self-contained and demonstrates specific functionality.

## Quick Start

\`\`\`bash
# Clone the repository
git clone https://github.com/algorandfoundation/algokit-subscriber-py.git
cd algokit-subscriber-py

# Install dependencies
uv sync

# Run an example
cd examples/subscriber
uv run python 01_basic_poll_once.py
\`\`\`

## Prerequisites

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) installed
- [AlgoKit CLI](https://github.com/algorandfoundation/algokit-cli) installed
- LocalNet running for network examples (\`algokit localnet start\`)

## Examples (${allExamples.length})

<table>
<thead><tr><th>Example</th><th>Description</th></tr></thead>
<tbody>
${tableRows}
</tbody>
</table>

<style>
{\`
table {
  width: 100%;
}
table td:first-child {
  white-space: nowrap;
  font-weight: 500;
}
table td:last-child {
  width: 100%;
}
table td p {
  margin: 0.25rem 0;
}
table td ul {
  margin: 0.25rem 0;
  padding-left: 1.25rem;
}
\`}
</style>
`,
)

console.log(`Generated ${allExamples.length} example MDX files + index page in docs/src/content/docs/examples/`)