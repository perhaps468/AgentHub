/**
 * PPT 数据解析工具
 *
 * 职责：
 * 1. 解析后端原始消息（兼容字符串 JSON / payload 嵌套 / 直接对象三种来源）
 * 2. 产出前端统一可消费的 PptPreviewModel 结构
 * 3. 为每一页补齐本地图片地址
 */
import type { PptPageItem, PptMessageData } from '../types/message'
import type { PptSlideViewModel } from '../types/agenthub'
import { resolvePptImage } from '../constants/ppt-image-map'

/** 默认 PPT 标题（当后端未提供时使用） */
const DEFAULT_PPT_TITLE = '汇报 PPT'
/** 默认 Agent 角色标签 */
const DEFAULT_AGENT_ROLE = 'Agent'

/**
 * 解析原始消息，返回标准化后的 PPT 预览模型
 *
 * 兼容以下输入来源：
 * - 历史消息：message 字段直接是 JSON 字符串或对象
 * - 实时消息：payload 中包含 ppt_data
 * - 嵌套消息：message 是 JSON 字符串，内含嵌套 payload
 *
 * @param raw - 消息的 message 字段或 payload 对象
 * @returns 标准化后的 PPT 模型，ppt_data 为空时返回 null
 */
export function buildPptPreviewModel(raw: string | Record<string, unknown> | null | undefined): PptPreviewModel | null {
  const payload = parsePptPayload(raw)
  if (!payload || !payload.ppt_data || payload.ppt_data.length === 0) {
    return null
  }

  const slides: PptSlideViewModel[] = (payload.ppt_data || []).map((page, index) => {
    const pageTitle = page.pageTitle || `第 ${index + 1} 页`
    const bullets = normalizeBullets(page.pageContent)

    return {
      id: `slide-${index}`,
      title: pageTitle,
      bullets,
      imgTag: page.imgTag || '',
      imageUrl: resolvePptImage(page.imgTag || '', index),
    }
  })

  return {
    title: `${payload.agent_role || DEFAULT_AGENT_ROLE} ${DEFAULT_PPT_TITLE}`,
    agentRole: payload.agent_role || DEFAULT_AGENT_ROLE,
    createdAt: payload.timestamp || '',
    slides,
  }
}

/**
 * 从多种原始数据格式中解析出 PptMessageData 结构
 *
 * 后端推送时，数据可能出现在不同位置：
 * - 直接作为 message 字符串传入
 * - 作为 payload 对象传入
 * - 作为 message 字段内嵌的 JSON 字符串传入
 */
function parsePptPayload(raw: string | Record<string, unknown> | null | undefined): PptMessageData | null {
  if (!raw) return null

  // 情况 1：已经是对象，直接取 ppt_data
  if (typeof raw === 'object') {
    const obj = raw as Record<string, unknown>
    if (obj.ppt_data) return raw as unknown as PptMessageData

    // 情况 2：message 字段在 payload 里
    const messageField = obj.message
    if (typeof messageField === 'string') {
      return tryParseMessage(messageField)
    }

    return null
  }

  // 情况 3：message 是 JSON 字符串
  if (typeof raw === 'string') {
    return tryParseMessage(raw)
  }

  return null
}

/**
 * 尝试将字符串解析为 PptMessageData，失败返回 null
 */
function tryParseMessage(message: string): PptMessageData | null {
  try {
    const parsed = JSON.parse(message)
    if (parsed && typeof parsed === 'object' && parsed.ppt_data) {
      return parsed as PptMessageData
    }
  } catch {
    // 不是合法 JSON，返回 null
  }
  return null
}

/**
 * 统一处理 pageContent 字段，确保返回字符串数组
 * 兜底空值、异常类型
 */
function normalizeBullets(raw: unknown): string[] {
  if (Array.isArray(raw)) {
    return raw.filter((item): item is string => typeof item === 'string')
  }
  return []
}
