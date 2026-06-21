// 뉴스 발행시각 등 상대 시간 표시 (F500). 최근이면 'n분/시간/일 전', 오래되면 날짜.
export function timeAgo(value) {
  if (!value) return ''
  const then = new Date(value)
  if (Number.isNaN(then.getTime())) return ''
  const diffSec = Math.floor((Date.now() - then.getTime()) / 1000)

  if (diffSec < 60) return '방금'
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}분 전`
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}시간 전`
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}일 전`

  return then.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}
