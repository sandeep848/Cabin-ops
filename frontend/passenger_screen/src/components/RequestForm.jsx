import React from 'react';
import { IconMic, IconSend, IconX } from './Icons';

export default function RequestForm({
  requestText,
  setRequestText,
  submitting,
  onSubmit,
  assistantReply,
  submitError,
  textareaRef,
  isRecording,
  isTranscribing,
  voiceError,
  recordingSeconds,
  handleMicClick,
}) {
  const formatRecordingTime = (secs) => {
    const m = Math.floor(secs / 60).toString().padStart(2, '0');
    const s = (secs % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="request-card">
      <div className="request-input-wrapper">
        <textarea
          ref={textareaRef}
          className="request-textarea"
          rows={3}
          placeholder="Ask anything or speak"
          value={requestText}
          onChange={(e) => setRequestText(e.target.value)}
          disabled={submitting || isRecording || isTranscribing}
          onKeyDown={handleKeyDown}
        />

        {/* Mic Icon Inside Textarea wrapper on the right */}
        <button
          className={`btn-mic-inside ${
            voiceError ? 'state-error' : isRecording ? 'state-recording' : isTranscribing ? 'state-transcribing' : 'state-idle'
          }`}
          onClick={handleMicClick}
          disabled={submitting}
          title={voiceError ? 'Clear error' : isRecording ? 'Stop recording' : isTranscribing ? 'Transcribing…' : 'Start voice input'}
          type="button"
        >
          {voiceError ? (
            <IconX size={14} />
          ) : isRecording ? (
            <span className="pulsing-red-dot" />
          ) : isTranscribing ? (
            <span className="spinner-inside" />
          ) : (
            <IconMic size={14} />
          )}
        </button>
      </div>

      <div className="request-actions-row">
        <div className="request-actions-left">
          {isRecording && (
            <span className="recording-timer">{formatRecordingTime(recordingSeconds)}</span>
          )}
          {isTranscribing && (
            <span className="recording-timer" style={{ color: 'var(--color-accent)' }}>
              Transcribing…
            </span>
          )}
          {voiceError && (
            <span className="recording-timer" style={{ color: 'var(--color-danger)' }}>
              Voice Input Error
            </span>
          )}
        </div>

        <div className="request-actions-right">
          <span className="char-count">{requestText.length} / 500</span>
          <button
            className="btn-send"
            onClick={() => onSubmit()}
            disabled={!requestText.trim() || submitting || isRecording || isTranscribing}
          >
            {submitting ? (
              <>
                <span className="spinner" />
                Sending…
              </>
            ) : (
              <>
                <IconSend size={13} />
                Send request
              </>
            )}
          </button>
        </div>
      </div>

      {submitError && <p className="submit-error">{submitError}</p>}

      {/* Assistant reply */}
      {assistantReply && (
        <div className="assistant-reply">
          <div className="assistant-reply-header">
            <span className="assistant-reply-label">ApexAir Assistant</span>
            <span
              className={`assistant-reply-badge ${
                assistantReply.crew_required
                  ? 'assistant-reply-badge--crew'
                  : 'assistant-reply-badge--auto'
              }`}
            >
              {assistantReply.crew_required ? 'Crew Dispatched' : 'Auto-Answered'}
            </span>
          </div>
          <p className="assistant-reply-text">
            {assistantReply.response ||
              assistantReply.message ||
              assistantReply.action ||
              'Your request has been received.'}
          </p>
        </div>
      )}
    </div>
  );
}
