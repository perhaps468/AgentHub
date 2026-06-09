/**
 * PPT 文件导出工具
 *
 * 职责：将前端标准 PptPreviewModel 数据转换为 .pptx 文件并在浏览器触发下载
 * 依赖：pptxgenjs（浏览器端直接运行，无需后端）
 */
import PptxGenJS from 'pptxgenjs'
import type { PptPreviewModel, PptSlideViewModel } from '../types/agenthub'

/** 幻灯片尺寸：宽33cm，高19cm */
const SLIDE_W = 33
const SLIDE_H = 19

/** 整页内容安全边距 */
const FRAME_PAD_X = 0.92
const FRAME_PAD_Y = 0.81
const FRAME_W = SLIDE_W - FRAME_PAD_X * 2   // 31.16 cm
const FRAME_H = SLIDE_H - FRAME_PAD_Y * 2   // 17.38 cm

/** 顶部标题遮罩区（白色，透明度90%），高度加大以容纳80pt标题 */
const TOP_OVERLAY_X = 1.58
const TOP_OVERLAY_Y = 1.0
const TOP_OVERLAY_W = 29.83
const TOP_OVERLAY_H = 6.5   // 原4.2，增至6.5cm

/** 底部要点遮罩区（白色，透明度90%），高度加大以容纳50pt多行要点 */
const BULLETS_OVERLAY_X = 1.72
const BULLETS_OVERLAY_Y = 10.2  // 上移给底部留白
const BULLETS_OVERLAY_W = 29.57
const BULLETS_OVERLAY_H = 7.8   // 原6.0，增至7.8cm

/** 无要点空态遮罩区（白色，透明度90%） */
const EMPTY_OVERLAY_X = 3.96
const EMPTY_OVERLAY_Y = 13.0
const EMPTY_OVERLAY_W = 25.08
const EMPTY_OVERLAY_H = 2.2

/** 底图：与页面预览兜底图一致 */
const FALLBACK_IMAGE = '/PPT/动漫.jpg'

/**
 * 将 PPT 模型生成为 .pptx Blob。
 * 供直接下载和上传到工作区两用。
 */
export async function exportPptToBlob(model: PptPreviewModel): Promise<Blob> {
  const pptx = new PptxGenJS({ units: 'cm' })
  pptx.defineLayout({ name: 'CUSTOM', width: SLIDE_W, height: SLIDE_H })
  pptx.layout = 'CUSTOM'

  pptx.title = model.title
  pptx.author = model.agentRole || 'AgentHub'
  pptx.subject = 'AgentHub PPT Preview Export'
  pptx.company = 'AgentHub'

  for (const [index, slideData] of model.slides.entries()) {
    const slide = pptx.addSlide()
    // 深色背景，保证白色文字在透明遮罩下清晰
    slide.background = { color: '0F172A' }

    renderSlideBackground(slide, slideData)
    renderTopOverlay(slide, slideData, index + 1, model.slides.length)
    renderBottomOverlay(slide, slideData)
  }

  return await pptx.write('blob')
}

/**
 * 将 PPT 模型生成为 .pptx 文件并触发浏览器下载（原有行为保留）
 */
export async function exportPpt(
  model: PptPreviewModel,
  fileName = 'presentation',
): Promise<void> {
  const blob = await exportPptToBlob(model)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${fileName}.pptx`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

function renderSlideBackground(
  slide: ReturnType<typeof PptxGenJS.prototype.addSlide>,
  slideData: PptSlideViewModel,
): void {
  const imagePath = slideData.imageUrl || FALLBACK_IMAGE

  try {
    slide.addImage({
      path: imagePath,
      x: FRAME_PAD_X,
      y: FRAME_PAD_Y,
      w: FRAME_W,
      h: FRAME_H,
    })
  } catch {
    console.warn(`[ppt-export] 图片加载失败，已使用底色替代: ${imagePath}`)
  }

  // 添加一个几乎透明的圆角边框，增强图片质感
  slide.addShape('roundRect', {
    x: FRAME_PAD_X,
    y: FRAME_PAD_Y,
    w: FRAME_W,
    h: FRAME_H,
    rectRadius: 0.26,
    line: { color: 'FFFFFF', transparency: 80, pt: 1 },
    fill: { color: 'FFFFFF', transparency: 100 },
  })
}

function renderTopOverlay(
  slide: ReturnType<typeof PptxGenJS.prototype.addSlide>,
  slideData: PptSlideViewModel,
  pageNum: number,
  totalPages: number,
): void {
  // 白色遮罩，透明度90%（几乎全透明，透出背景图片）
  slide.addShape('roundRect', {
    x: TOP_OVERLAY_X,
    y: TOP_OVERLAY_Y,
    w: TOP_OVERLAY_W,
    h: TOP_OVERLAY_H,
    rectRadius: 0.26,
    line: { color: 'FFFFFF', transparency: 100, pt: 0 },
    fill: { color: 'FFFFFF', transparency: 90 },
    shadow: {
      type: 'outer',
      color: '000000',
      blur: 4,
      angle: 45,
      opacity: 0.2,
      offset: 1,
    },
  })

  // 页码字体 24pt，白色
  slide.addText(`第 ${pageNum} / ${totalPages} 页`, {
    x: TOP_OVERLAY_X + 0.6,
    y: TOP_OVERLAY_Y + 0.4,
    w: 5.0,
    h: 0.9,
    fontSize: 24,
    color: 'FFFFFF',
    bold: false,
    margin: 0,
  })

  // 标题字体 80pt，白色，粗体
  slide.addText(slideData.title || `第 ${pageNum} 页`, {
    x: TOP_OVERLAY_X + 0.6,
    y: TOP_OVERLAY_Y + 1.4,
    w: TOP_OVERLAY_W - 1.2,
    h: 3.5,
    fontSize: 80,
    bold: true,
    color: 'FFFFFF',
    margin: 0,
    fit: 'shrink',
    valign: 'middle',
  })
}

function renderBottomOverlay(
  slide: ReturnType<typeof PptxGenJS.prototype.addSlide>,
  slideData: PptSlideViewModel,
): void {
  if (!slideData.bullets?.length) {
    // 空状态遮罩
    slide.addShape('roundRect', {
      x: EMPTY_OVERLAY_X,
      y: EMPTY_OVERLAY_Y,
      w: EMPTY_OVERLAY_W,
      h: EMPTY_OVERLAY_H,
      rectRadius: 0.26,
      line: { color: 'FFFFFF', transparency: 80, pt: 0.8 },
      fill: { color: 'FFFFFF', transparency: 90 },
    })

    slide.addText('本页无要点内容', {
      x: EMPTY_OVERLAY_X,
      y: EMPTY_OVERLAY_Y + 0.5,
      w: EMPTY_OVERLAY_W,
      h: 1.0,
      align: 'center',
      fontSize: 32,
      color: 'FFFFFF',
      margin: 0,
    })
    return
  }

  // 底部要点遮罩（白色，透明度90%）
  slide.addShape('roundRect', {
    x: BULLETS_OVERLAY_X,
    y: BULLETS_OVERLAY_Y,
    w: BULLETS_OVERLAY_W,
    h: BULLETS_OVERLAY_H,
    rectRadius: 0.33,
    line: { color: 'FFFFFF', transparency: 80, pt: 0.8 },
    fill: { color: 'FFFFFF', transparency: 90 },
    shadow: {
      type: 'outer',
      color: '000000',
      blur: 4,
      angle: 45,
      opacity: 0.2,
      offset: 1,
    },
  })

  const bulletTexts = buildBulletRuns(slideData)
  slide.addText(bulletTexts, {
    x: BULLETS_OVERLAY_X + 0.8,
    y: BULLETS_OVERLAY_Y + 0.8,
    w: BULLETS_OVERLAY_W - 1.6,
    h: BULLETS_OVERLAY_H - 1.2,
    margin: 0,
    breakLine: false,
    valign: 'middle',
    fit: 'shrink',
  })
}

function buildBulletRuns(slideData: PptSlideViewModel) {
  return slideData.bullets.map((text, index) => ({
    text,
    options: {
      bullet: { indent: 14 },
      breakLine: index < slideData.bullets.length - 1,
      color: 'FFFFFF',      // 白色文字
      fontSize: 50,         // 正文要求 50pt
      bold: false,
      paraSpaceAfter: 12,   // 大字体段落间距加大
      hanging: 2,
    },
  }))
}