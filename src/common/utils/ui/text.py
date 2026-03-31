def buildEditModeMessage(formattedText: str, isCaption: bool) -> str:
    separator = '-' * 10
    return (
        f"<b>✏️ Edit mode activated</b>\n\n"
        f"<b>Current text:</b>\n"
        f"{separator}\n"
        f"<blockquote>{formattedText}</blockquote>\n"
        f"{separator}\n"
        f"<b>Send the new {'caption' if isCaption else 'text'}</b>"
    )
