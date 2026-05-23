import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchDefaultAgent } from '@/api/modules/agents'
import type { AgentProfile } from '@/types/agenthub'

export const useAgentStore = defineStore('agent', () => {
  const agent = ref<AgentProfile | null>(null)

  async function fetchDefaultAgentAction() {
    if (agent.value) return
    agent.value = await fetchDefaultAgent()
  }

  return { agent, fetchDefaultAgent: fetchDefaultAgentAction }
})
