/**
 * PPT 本地图片素材映射
 *
 * 基于 imgTag 关键词匹配本地图片，优先级：
 * 1. 精确匹配关键词
 * 2. 模糊包含匹配
 * 3. 默认图兜底
 *
 * 同一标签多页时按 pageIndex 轮转分配不同图片
 *
 * 图片文件统一放在 /PPT/ 目录下（对应 frontend/public/PPT/）
 */

/** 单个图片素材配置 */
export interface PptImageAsset {
  /** 唯一标识 */
  key: string
  /** 公开访问路径（public 目录下的相对路径） */
  url: string
  /** 触发该图片的关键词列表（不区分大小写匹配） */
  keywords: string[]
}

/** 所有 PPT 图片素材清单 */
export const PPT_IMAGE_ASSETS: PptImageAsset[] = [
  {
    key: '教育',
    url: '/PPT/教育1.jpg',
    keywords: ['教育']
  },
  {
    key: '教育',
    url: '/PPT/教育2.jpg',
    keywords: ['教育']
  },
  {
    key: '教育',
    url: '/PPT/教育3.jpg',
    keywords: ['教育']
  },
  {
    key: '教育',
    url: '/PPT/教育4.jpg',
    keywords: ['教育']
  },
  {
    key: '教育',
    url: '/PPT/教育5.jpg',
    keywords: ['教育']
  }
]

/** 默认兜底图片（当关键词均未匹配时使用） */
export const DEFAULT_PPT_IMAGE = '/PPT/教育2.jpg'

/**
 * 根据 imgTag 从本地素材库中匹配合适的图片路径
 *
 * 匹配逻辑：
 * 1. 将 imgTag 统一转小写后，在所有素材关键词列表中做包含匹配
 * 2. 返回第一个匹配成功的素材 URL（无 pageIndex 时）
 *    或按 pageIndex 轮转分配命中的多张素材（传入 pageIndex 时）
 * 3. 无任何匹配时返回默认图
 *
 * @param imgTag    - 后端下发的图片风格描述（中文/英文均可）
 * @param pageIndex - 传入当前页索引（从 0 开始），同一标签的多页会轮转分配不同图片
 * @returns 匹配到的本地图片公开路径
 */
export function resolvePptImage(imgTag: string, pageIndex?: number): string {
  if (!imgTag || typeof imgTag !== 'string') {
    return DEFAULT_PPT_IMAGE
  }

  const normalized = imgTag.toLowerCase().trim()
  if (!normalized) {
    return DEFAULT_PPT_IMAGE
  }

  // 收集所有匹配到的资产
  const matchedAssets: PptImageAsset[] = []
  for (const asset of PPT_IMAGE_ASSETS) {
    const matched = asset.keywords.some((keyword) =>
      normalized.includes(keyword.toLowerCase()),
    )
    if (matched) {
      matchedAssets.push(asset)
    }
  }

  if (matchedAssets.length === 0) {
    return DEFAULT_PPT_IMAGE
  }

  // 有 pageIndex → 轮转分配；有 pageIndex=0 但命中多个 → 取第一个
  if (pageIndex !== undefined && pageIndex >= 0) {
    const pick = pageIndex % matchedAssets.length
    return matchedAssets[pick].url
  }

  // 无 pageIndex → 返回第一个匹配（向后兼容）
  return matchedAssets[0].url
}
