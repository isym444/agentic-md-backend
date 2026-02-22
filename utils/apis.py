from utils.constants import Constants
from google import genai
from supabase import create_client, Client
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

supabase: Client = create_client(
    Constants.SUPABASE_URL,
    Constants.SUPABASE_KEY
)

llm_client: genai.Client = genai.Client(
    api_key=Constants.GEMINI_API_KEY
)

elevenlabs_client: ElevenLabs = ElevenLabs(
    api_key=Constants.ELEVENLABS_API_KEY
)