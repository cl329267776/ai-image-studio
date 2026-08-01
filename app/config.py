import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    API_PROVIDER = os.getenv("API_PROVIDER", "jimeng")  # jimeng | ark
    JIMENG_ACCESS_KEY = os.getenv("JIMENG_ACCESS_KEY", "")
    JIMENG_SECRET_KEY = os.getenv("JIMENG_SECRET_KEY", "")
    ARK_API_KEY = os.getenv("ARK_API_KEY", "")
    PORT = int(os.getenv("PORT", "8000"))
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

    @property
    def jimeng_ready(self) -> bool:
        return bool(self.JIMENG_ACCESS_KEY and self.JIMENG_SECRET_KEY)

    @property
    def ark_ready(self) -> bool:
        return bool(self.ARK_API_KEY)


config = Config()
