import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import ChatInputArea from './Chat-input-area.vue'

describe('ChatInputArea', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders a wechat-like composer with two tools and a disabled send button by default', async () => {
    const wrapper = mount(ChatInputArea, {
      props: {
        sessionId: '2',
      },
      global: {
        stubs: {
          Input: {
            props: ['value'],
            emits: ['update:value', 'send'],
            template:
              '<textarea data-testid="composer-editor" :value="value" @input="$emit(\'update:value\', $event.target.value)" />',
          },
        },
      },
    })

    expect(wrapper.find('.composer-toolbar').exists()).toBe(true)
    expect(wrapper.findAll('.tool-btn')).toHaveLength(4)
    expect(wrapper.find('.send-btn').attributes('disabled')).toBeDefined()

    await wrapper.find('[data-testid="composer-editor"]').setValue('hello')

    expect(wrapper.find('.send-btn').attributes('disabled')).toBeUndefined()
  })

  it('updates selected agent summary when the composer emits structured changes', async () => {
    const wrapper = mount(ChatInputArea, {
      props: {
        sessionId: 'session-1',
      },
      global: {
        stubs: {
          Input: {
            props: ['value', 'sessionAgentOptions'],
            emits: ['structured-change'],
            template: `
              <button
                class="emit-structured-change"
                @click="$emit('structured-change', {
                  text: 'hello',
                  targetAgentIds: ['agent-a'],
                  selectedAgents: [{ id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' }],
                  nodes: [
                    { type: 'agent-chip', agent: { id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' } },
                    { type: 'text', content: 'hello' },
                  ],
                })"
              >
                emit
              </button>
            `,
          },
        },
      },
    })

    await wrapper.get('.emit-structured-change').trigger('click')

    const pills = wrapper.findAll('.selected-agent-pill')
    expect(pills).toHaveLength(1)
    expect(pills[0].text()).toContain('Alpha')
    expect(wrapper.emitted('selection-change')).toEqual([
      [
        [{ id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' }],
      ],
    ])
  })

  it('shows selected agent feedback immediately when insertAgentChip is called through the exposed API', async () => {
    const wrapper = mount(ChatInputArea, {
      props: {
        sessionId: 'session-1',
      },
      global: {
        stubs: {
          Input: {
            props: ['value', 'sessionAgentOptions', 'handlerSubmitMsg'],
            template: '<div class="input-stub"></div>',
            methods: {
              insertAgentChip() {},
              getStructuredValue() {
                return {
                  text: '',
                  targetAgentIds: ['agent-a'],
                  selectedAgents: [
                    { id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' },
                  ],
                  nodes: [
                    { type: 'agent-chip', agent: { id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' } },
                  ],
                }
              },
            },
          },
        },
      },
    })

    ;(wrapper.vm as unknown as { insertAgentChip: (agent: any) => void }).insertAgentChip({
      id: 'agent-a',
      name: 'Alpha',
      avatar: null,
      status: 'online',
      role: 'frontend',
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.selected-agent-pill')).toHaveLength(1)
    expect(wrapper.find('.selected-agent-pill').text()).toContain('@Alpha')
    expect(wrapper.emitted('selection-change')?.at(-1)).toEqual([
      [{ id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' }],
    ])
  })

  it('emits the structured send payload and clears selection after submit', async () => {
    const wrapper = mount(ChatInputArea, {
      props: {
        sessionId: 'session-1',
      },
      global: {
        stubs: {
          Input: {
            props: ['value', 'sessionAgentOptions', 'handlerSubmitMsg'],
            emits: ['structured-change'],
            template: '<div class="input-stub"></div>',
            methods: {
              getStructuredValue() {
                return {
                  text: 'ship it',
                  targetAgentIds: ['agent-a'],
                  selectedAgents: [
                    { id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' },
                  ],
                  nodes: [
                    { type: 'agent-chip', agent: { id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' } },
                    { type: 'text', content: 'ship it' },
                  ],
                }
              },
              clear() {},
            },
          },
        },
      },
    })

    ;(wrapper.vm as unknown as { handleComposerPayload: (payload: any) => void }).handleComposerPayload({
      text: 'ship it',
      targetAgentIds: ['agent-a'],
      selectedAgents: [{ id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' }],
      nodes: [
        { type: 'agent-chip', agent: { id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' } },
        { type: 'text', content: 'ship it' },
      ],
    })
    await wrapper.vm.$nextTick()

    await wrapper.get('.send-btn').trigger('click')

    expect(wrapper.emitted('send')).toEqual([
      [
        {
          text: 'ship it',
          targetAgentIds: ['agent-a'],
          selectedAgents: [{ id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' }],
          nodes: [
            { type: 'agent-chip', agent: { id: 'agent-a', name: 'Alpha', avatar: null, status: 'online', role: 'frontend' } },
            { type: 'text', content: 'ship it' },
          ],
        },
      ],
    ])

    const selectionEvents = wrapper.emitted('selection-change') ?? []
    expect(selectionEvents.at(-1)).toEqual([[]])
    expect(wrapper.findAll('.selected-agent-pill')).toHaveLength(0)
  })
})
