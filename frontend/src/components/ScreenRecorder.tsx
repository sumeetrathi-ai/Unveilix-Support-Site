// Change log:
// [#002] 2026-06-22 — Sumeet — `hasClip` is now a controlled prop (was internal state) so the
//        button label resets to "Record screen" when the parent removes the attached clip.
// [#001] 2026-06-22 — Sumeet — File created. Real screen recording via getDisplayMedia +
//        MediaRecorder, producing a .webm Blob (spec §7). Live timer + click-to-stop; the
//        browser's own "Stop sharing" also ends the clip. Requires a secure context
//        (localhost counts).
import { useRef, useState } from "react"
import { useToast } from "../toast"
import { Icon } from "../ui"

function pickMime(): string {
  const candidates = ["video/webm;codecs=vp9", "video/webm;codecs=vp8", "video/webm"]
  for (const c of candidates) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(c)) return c
  }
  return "video/webm"
}

function fmt(s: number) {
  const m = String(Math.floor(s / 60)).padStart(2, "0")
  const sec = String(s % 60).padStart(2, "0")
  return `${m}:${sec}`
}

export function ScreenRecorder({
  onCapture,
  hasClip,
}: {
  onCapture: (blob: Blob, seconds: number) => void
  hasClip: boolean
}) {
  const toast = useToast()
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const recRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | undefined>(undefined)
  const secsRef = useRef(0)

  function stop() {
    recRef.current?.stop()
  }

  async function start() {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      toast.show("Screen recording isn't supported in this browser", "err")
      return
    }
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false })
      chunksRef.current = []
      const mime = pickMime()
      const mr = new MediaRecorder(stream, { mimeType: mime })
      mr.ondataavailable = (e) => {
        if (e.data.size) chunksRef.current.push(e.data)
      }
      mr.onstop = () => {
        window.clearInterval(timerRef.current)
        stream.getTracks().forEach((t) => t.stop())
        setRecording(false)
        const blob = new Blob(chunksRef.current, { type: mime })
        onCapture(blob, secsRef.current)
        toast.show("Recording attached")
      }
      stream.getVideoTracks()[0].addEventListener("ended", stop)
      mr.start()
      recRef.current = mr
      setSeconds(0)
      secsRef.current = 0
      setRecording(true)
      timerRef.current = window.setInterval(() => {
        secsRef.current += 1
        setSeconds(secsRef.current)
      }, 1000)
      toast.show("Screen recording started — pick a window or tab to share")
    } catch {
      /* user cancelled the share dialog */
    }
  }

  return (
    <button type="button" className={`drop ${recording ? "recording" : ""}`} onClick={recording ? stop : start}>
      {!recording ? (
        <span>
          <Icon.Video size={26} />
          <b>{hasClip ? "Re-record screen" : "Record screen"}</b>
          <small>{hasClip ? "Replace the attached clip" : "Capture the bug as it happens"}</small>
        </span>
      ) : (
        <span>
          <span className="rec-btn">
            <span className="rec-dot" />
            <b>Recording… click to stop</b>
          </span>
          <small style={{ fontFamily: "var(--mono)" }}>{fmt(seconds)}</small>
        </span>
      )}
    </button>
  )
}
