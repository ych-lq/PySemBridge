import fs from 'fs'
import path from 'path'

const { yasaLog, yasaWarning } = require('../../../util/format-util')

interface SemanticBridgeFacts {
  version?: string
  source_bridge?: string
  project?: string
  language?: string
  gap_types?: string[]
  yasa_injection?: {
    graph_facts?: Record<string, any[]>
    flow_facts?: Record<string, any[]>
  }
  validation?: any
  evidence?: any[]
}

function normalizeFactsPath(factsPath: string): string {
  return path.isAbsolute(factsPath) ? factsPath : path.resolve(path.join(process.cwd(), factsPath))
}

function countFactItems(facts: SemanticBridgeFacts): number {
  const graphFacts = facts.yasa_injection?.graph_facts || {}
  const flowFacts = facts.yasa_injection?.flow_facts || {}
  let count = 0
  for (const group of Object.values(graphFacts)) {
    if (Array.isArray(group)) count += group.length
  }
  for (const group of Object.values(flowFacts)) {
    if (Array.isArray(group)) count += group.length
  }
  return count
}

function validateFacts(facts: SemanticBridgeFacts, factsPath: string) {
  if (!facts || typeof facts !== 'object') {
    throw new Error(`Semantic bridge facts must be a JSON object: ${factsPath}`)
  }
  if (!facts.yasa_injection || typeof facts.yasa_injection !== 'object') {
    throw new Error(`Semantic bridge facts missing yasa_injection: ${factsPath}`)
  }
  if (!facts.yasa_injection.graph_facts && !facts.yasa_injection.flow_facts) {
    throw new Error(`Semantic bridge facts missing graph_facts/flow_facts: ${factsPath}`)
  }
}

function loadSemanticBridgeFacts(factsPath: string): SemanticBridgeFacts | null {
  if (!factsPath || factsPath.trim() === '') return null

  const absolutePath = normalizeFactsPath(factsPath)
  if (!fs.existsSync(absolutePath)) {
    throw new Error(`Semantic bridge facts file does not exist: ${absolutePath}`)
  }

  const facts = JSON.parse(fs.readFileSync(absolutePath, 'utf8')) as SemanticBridgeFacts
  validateFacts(facts, absolutePath)

  const factCount = countFactItems(facts)
  yasaLog(
    `Loaded semantic bridge facts: ${absolutePath} bridge=${facts.source_bridge || 'unknown'} facts=${factCount}`,
    'semantic-bridge'
  )

  if (factCount === 0) {
    yasaWarning(`Semantic bridge facts loaded but contain no graph/flow facts: ${absolutePath}`)
  }

  return facts
}

module.exports = {
  loadSemanticBridgeFacts,
}
