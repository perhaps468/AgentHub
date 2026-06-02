import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { createAgent, fetchAgentConfig, fetchAgents, fetchDefaultAgent, updateAgent } from '@/api/modules/agents'
import type { AgentProfile } from '@/types/agenthub'

function toSidebarAgent(agent: AgentProfile) {
  const capabilityTags = agent.capabilityTags || agent.capability_tags || []
  return {
    id: agent.id,
    name: agent.name,
    avatar: agent.avatar_url || agent.avatar || '',
    capabilityTags,
    description: agent.description,
    platform: agent.platform || 'custom',
    isCustom: !agent.is_builtin,
    role: agent.role,
    model: agent.model,
    system_prompt: agent.system_prompt,
  }
}

export const useAgentStore = defineStore('agent', () => {
  const agent = ref<AgentProfile | null>(null)
  const agents = ref<ReturnType<typeof toSidebarAgent>[]>([])
  const availableModels = ref<string[]>([])
  const availableCapabilityTags = ref<string[]>([])
  const isLoading = ref(false)

  const filteredAgents = computed(() => agents.value)

  async function fetchDefaultAgentAction() {
    if (agent.value) return agent.value
    agent.value = await fetchDefaultAgent()
    return agent.value
  }

  async function fetchAgentsAction() {
    isLoading.value = true
    try {
      const data = await fetchAgents({ include_builtin: true, include_inactive: false })
      agents.value = data.items.map(toSidebarAgent)
      return agents.value
    } finally {
      isLoading.value = false
    }
  }

  async function fetchAgentConfigAction() {
    const config = await fetchAgentConfig()
    availableModels.value = config.available_models
    availableCapabilityTags.value = config.available_capability_tags
    return config
  }

  async function createAgentAction(payload: Parameters<typeof createAgent>[0]) {
    const created = await createAgent(payload)
    agents.value = [toSidebarAgent(created), ...agents.value]
    return created
  }

  async function updateAgentAction(agentId: string, payload: Parameters<typeof updateAgent>[1]) {
    const updated = await updateAgent(agentId, payload)
    agents.value = agents.value.map((item) => (item.id === agentId ? toSidebarAgent(updated) : item))
    return updated
  }

  return {
    agent,
    agents,
    availableModels,
    availableCapabilityTags,
    isLoading,
    filteredAgents,
    fetchAgentConfig: fetchAgentConfigAction,
    fetchDefaultAgent: fetchDefaultAgentAction,
    fetchAgents: fetchAgentsAction,
    createAgent: createAgentAction,
    updateAgent: updateAgentAction,
  }
})
