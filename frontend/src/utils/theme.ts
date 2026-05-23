import { nextTick } from 'vue'
import { useThemeStore } from '../store/module/useThemeStore'

type ThemeMode = 'light' | 'dark' | string

type ThemeToggleEvent = MouseEvent

type DocumentWithTransition = Document & {
  startViewTransition?: (callback: () => Promise<void> | void) => {
    ready: Promise<void>
  }
}

export function toggleDark(event: ThemeToggleEvent, theme: ThemeMode) {
  const themeStore = useThemeStore()
  const x = event.clientX
  const y = event.clientY
  const endRadius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y))
  const isDark = theme === 'dark'
  const transitionDocument = document as DocumentWithTransition

  if (!transitionDocument.startViewTransition) {
    void themeStore.setTheme(theme)
    document.documentElement.className = theme
    console.log('主题已切换为:', theme)
    return
  }

  const transition = transitionDocument.startViewTransition(async () => {
    await themeStore.setTheme(theme)
    document.documentElement.className = theme
    await nextTick()
  })

  transition.ready.then(() => {
    const clipPath = [`circle(0px at ${x}px ${y}px)`, `circle(${endRadius}px at ${x}px ${y}px)`]
    document.documentElement.animate(
      {
        clipPath: isDark ? [...clipPath].reverse() : clipPath,
      },
      {
        duration: 300,
        easing: 'ease-out',
        pseudoElement: isDark ? '::view-transition-old(root)' : '::view-transition-new(root)',
      },
    )
  })

  console.log('主题已切换为:', theme)
}

