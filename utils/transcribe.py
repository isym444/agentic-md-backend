from utils.apis import elevenlabs_client as client

def transcribe_file(file_path: str) -> str:
    """
    Accepts a path to a WAV file and returns the transcription text.
    """
    with open(file_path, "rb") as f:
        transcription = client.speech_to_text.convert(
            file=f,
            model_id="scribe_v2"
        )
    return transcription.text