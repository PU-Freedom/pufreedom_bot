def buildEditModeMessage(isCaption: bool) -> str:
    return (
        "<b>✏️ Edit mode activated</b>\n\n"
        f"<b>Send the new {'caption' if isCaption else 'text'}</b> - the current version is above ☝️"
    )
