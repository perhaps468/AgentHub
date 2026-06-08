import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'

import MsgContent from './msg_content .vue'
import { useSessionStore } from '../../store/module/useSessionStore'
import { MessageType } from '../../types/messageType'

describe('MsgContent', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('shows quick actions in the context menu on right click', async () => {
    const wrapper = mount(MsgContent, {
      props: {
        right: false,
        msg: {
          id: 'msg-1',
          type: 'text',
          message: 'hello world',
        },
      },
      global: {
        stubs: {
          TextMsg: { template: '<div>text</div>' },
          EmojiMsg: { template: '<div>emoji</div>' },
          call_msg: { template: '<div>call</div>' },
          PptMsg: { template: '<div>ppt</div>' },
          transition: false,
        },
      },
    })

    expect(wrapper.find('.ctx-menu').exists()).toBe(false)

    await wrapper.find('.msg-content').trigger('contextmenu', {
      clientX: 120,
      clientY: 80,
    })
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(document.querySelector('.ctx-menu')).not.toBeNull()
    expect(document.querySelectorAll('.ctx-menu-item')).toHaveLength(2)
  })

  it('renders referenced ppt messages and opens ppt preview from the ppt card', async () => {
    const sessionStore = useSessionStore()
    const previewPayload = {
      title: 'Report PPT',
      agentRole: 'pm',
      createdAt: '2026-06-08T00:00:00Z',
      slides: [],
    }

    const wrapper = mount(MsgContent, {
      props: {
        right: true,
        msg: {
          id: 'ppt-1',
          type: MessageType.PptData,
          message: JSON.stringify({ ppt_data: [{ pageTitle: 'Intro', pageContent: [], imgTag: '' }] }),
          metadata: {
            reference: {
              content: 'original message that should stay visible',
            },
          },
        },
      },
      global: {
        stubs: {
          TextMsg: { template: '<div>text</div>' },
          EmojiMsg: { template: '<div>emoji</div>' },
          call_msg: { template: '<div>call</div>' },
          PptMsg: {
            props: ['msg', 'right'],
            emits: ['preview'],
            template: '<button class="ppt-stub" @click="$emit(\'preview\', previewPayload)">ppt</button>',
            data: () => ({ previewPayload }),
          },
          transition: false,
        },
      },
    })

    expect(wrapper.find('.msg-reference-text').text()).toContain('original message that should stay visible')
    expect(wrapper.find('.ppt-stub').exists()).toBe(true)

    await wrapper.get('.ppt-stub').trigger('click')

    expect(sessionStore.streamState.previewPpt).toEqual(previewPayload)
  })
})
