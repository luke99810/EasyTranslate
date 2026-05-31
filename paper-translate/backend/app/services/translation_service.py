"""Translation service implementations.

Core translation pipeline inspired by academic translation tools like 小绿鲸:
1. Paragraph-level text extraction (not span-level)
2. Formula/protection placeholder replacement
3. Academic-style translation with context preservation
4. Terminology consistency within document
"""

import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
import re
import logging

from app.models.schemas import TranslationProvider

logger = logging.getLogger(__name__)


class TranslationService(ABC):
    """Abstract base class for translation services."""

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh"
    ) -> str:
        """Translate text.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            Translated text
        """
        pass

    def protect_formulas(self, text: str) -> Tuple[str, List[str]]:
        """Protect formulas by replacing with placeholders.

        Args:
            text: Original text

        Returns:
            Tuple of (protected_text, formulas_list)
        """
        formulas = []
        protected = text

        # LaTeX formula patterns (display math first, then inline)
        patterns = [
            r'\$\$[\s\S]+?\$\$',          # $$...$$ display math (multiline)
            r'\\\[[\s\S]+?\\\]',          # \[...\] display math
            r'\\begin\{equation\}[\s\S]*?\\end\{equation\}',
            r'\\begin\{align\}[\s\S]*?\\end\{align\}',
            r'\\begin\{eqnarray\}[\s\S]*?\\end\{eqnarray\}',
            r'\\begin\{gather\}[\s\S]*?\\end\{gather\}',
            r'\\begin\{matrix\}[\s\S]*?\\end\{matrix\}',
            r'\$[^$\n]+\$',              # $...$ inline math
            r'\\\([^)]+\\\)',             # \(...\) inline math
        ]

        for pattern in patterns:
            matches = list(re.finditer(pattern, protected, re.DOTALL))
            for match in reversed(matches):
                formula = match.group()
                formulas.insert(0, formula)
                placeholder = f"[[FORMULA_{len(formulas)-1}]]"
                protected = protected[:match.start()] + placeholder + protected[match.end():]

        return protected, formulas

    def restore_formulas(self, text: str, formulas: List[str]) -> str:
        """Restore formulas from placeholders.

        Args:
            text: Text with placeholders
            formulas: List of original formulas

        Returns:
            Text with formulas restored
        """
        result = text
        for i, formula in enumerate(formulas):
            placeholder = f"[[FORMULA_{i}]]"
            result = result.replace(placeholder, formula)
        return result


class GoogleTranslateService(TranslationService):
    """Free translation via MyMemory API (accessible from China, no API key needed).

    Falls back to GoogleTranslator via deep-translator if MyMemory is unavailable.
    Note: Google Translate (translate.google.com) is blocked in mainland China,
    so we use MyMemory as the primary free engine.

    MyMemory has a 500 char limit per request — long texts are auto-chunked.
    """

    MYMEMORY_MAX_CHARS = 500

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh"
    ) -> str:
        """Translate using MyMemory (primary) or GoogleTranslator (fallback)."""
        if not text.strip():
            return text

        protected_text, formulas = self.protect_formulas(text)

        # MyMemory language codes (ISO 639-1)
        lang_map = {"zh": "zh-CN", "en": "en", "ja": "ja", "ko": "ko",
                     "de": "de", "fr": "fr", "es": "es", "ru": "ru"}
        target = lang_map.get(target_lang, target_lang)
        source = lang_map.get(source_lang, source_lang)

        # Split long text into chunks for MyMemory (500 char limit)
        chunks = self._split_text(protected_text, self.MYMEMORY_MAX_CHARS)
        translated_parts = []

        for chunk in chunks:
            if not chunk.strip():
                translated_parts.append(chunk)
                continue

            chunk_translated = await self._translate_chunk(chunk, source, target)
            translated_parts.append(chunk_translated)
            # Rate limiting
            await asyncio.sleep(0.5)

        translated = "".join(translated_parts)
        return self.restore_formulas(translated, formulas)

    async def _translate_chunk(self, text: str, source: str, target: str) -> str:
        """Try MyMemory first, then GoogleTranslator as fallback."""
        # MyMemory often returns "NO QUERY SPECIFIED", "0%", empty string, or the
        # original text unchanged when daily quota is exceeded.  Treat all of
        # these as failures so we can fall back gracefully.
        _INVALID_RESULTS = {"", "0%", "NO QUERY SPECIFIED", "QUERY LENGTH LIMIT EXCEEDED"}

        try:
            loop = asyncio.get_event_loop()

            def _do_translate_mymemory():
                from deep_translator import MyMemoryTranslator
                mt = MyMemoryTranslator(source=source, target=target)
                result = mt.translate(text)
                # Validate: reject known quota-exhaustion sentinel values
                if result in _INVALID_RESULTS or result.strip() == text.strip():
                    raise Exception(f"MyMemory 返回无效结果: {result!r}")
                return result

            return await loop.run_in_executor(None, _do_translate_mymemory)

        except Exception as e1:
            logger.warning(f"MyMemory translation failed: {e1}, trying GoogleTranslator...")
            try:
                loop = asyncio.get_event_loop()

                def _do_translate_google():
                    from deep_translator import GoogleTranslator
                    gt = GoogleTranslator(source=source, target=target)
                    result = gt.translate(text)
                    if not result or result.strip() in _INVALID_RESULTS:
                        raise Exception(f"GoogleTranslator 返回无效结果: {result!r}")
                    return result

                return await loop.run_in_executor(None, _do_translate_google)

            except Exception as e2:
                logger.error(f"Google Translate fallback also failed: {e2}")
                raise Exception(f"免费翻译引擎不可用（MyMemory: {e1}，Google: {e2}）。建议配置 DeepL 或 OpenAI/DeepSeek API Key 获得更好的翻译体验。")

    def _split_text(self, text: str, max_length: int) -> List[str]:
        """Split text at sentence boundaries within max_length."""
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_length:
                current += (" " if current else "") + sentence
            else:
                if current:
                    chunks.append(current)
                # Single sentence too long: split at spaces
                if len(sentence) > max_length:
                    words = sentence.split(' ')
                    word_current = ""
                    for word in words:
                        if len(word_current) + len(word) + 1 <= max_length:
                            word_current += (" " if word_current else "") + word
                        else:
                            if word_current:
                                chunks.append(word_current)
                            word_current = word
                    current = word_current
                else:
                    current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text]


class BaiduTranslateService(TranslationService):
    """Baidu Translate API implementation. Requires valid APP ID and Secret Key.

    Note: Baidu standard API has a 600 char limit per request.
    Long texts are automatically split into sentences within this limit.
    """

    # Max chars per request (Baidu standard API limit)
    MAX_CHARS = 600

    def __init__(self, app_id: str = "", secret_key: str = ""):
        self.app_id = app_id
        self.secret_key = secret_key
        self.base_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh"
    ) -> str:
        """Translate using Baidu Translate API with auto-splitting for long texts."""
        if not text.strip():
            return text

        protected_text, formulas = self.protect_formulas(text)

        # Baidu language code mapping
        lang_map = {"zh": "zh", "en": "en", "ja": "jp", "ko": "kor",
                     "de": "de", "fr": "fra", "es": "spa", "ru": "ru"}
        target = lang_map.get(target_lang, target_lang)
        source = lang_map.get(source_lang, source_lang)

        # Split text into chunks within Baidu's 600 char limit
        chunks = self._split_for_baidu(protected_text, self.MAX_CHARS)

        translated_parts = []
        for chunk in chunks:
            if not chunk.strip():
                translated_parts.append(chunk)
                continue
            translated = await self._translate_single(chunk, source, target)
            translated_parts.append(translated)
            # Baidu QPS limit: ~1 req/sec for standard API
            await asyncio.sleep(1.1)

        translated = "".join(translated_parts)
        return self.restore_formulas(translated, formulas)

    async def _translate_single(self, text: str, source: str, target: str) -> str:
        """Translate a single chunk within Baidu's char limit."""
        import hashlib
        import random

        salt = str(random.randint(32768, 65536))
        sign = hashlib.md5(
            f"{self.app_id}{text}{salt}{self.secret_key}".encode()
        ).hexdigest()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                self.base_url,
                params={
                    "q": text,
                    "from": source,
                    "to": target,
                    "appid": self.app_id,
                    "salt": salt,
                    "sign": sign
                }
            )
            response.raise_for_status()
            data = response.json()

            if "trans_result" in data:
                return "".join([item["dst"] for item in data["trans_result"]])
            else:
                error_code = data.get("error_code", "unknown")
                error_msg = data.get("error_msg", "")
                # Baidu sometimes omits error_msg; log full response for debugging
                logger.error(f"Baidu API error: code={error_code}, msg={error_msg}, full_response={data}")
                # Common error codes
                _BAIDU_ERRORS = {
                    "54001": "签名错误(APP ID 或 Secret Key 不正确)",
                    "54003": "访问频率受限，请稍后重试",
                    "54004": "账户余额不足",
                    "54005": "长query请求频繁，请降低频率",
                    "58000": "客户端IP非法",
                    "58001": "语言不支持",
                    "58002": "服务关闭",
                    "54000": "必填参数为空",
                    "58003": "IP被禁用，请联系百度翻译客服",
                }
                detail = _BAIDU_ERRORS.get(str(error_code), error_msg or str(data))
                raise Exception(f"百度翻译 API 错误 ({error_code}): {detail}")

    def _split_for_baidu(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks that respect Baidu's char limit.

        Splits at sentence boundaries (. ! ?) when possible,
        keeping chunks under max_length.
        """
        if len(text) <= max_length:
            return [text]

        chunks = []
        current = ""

        # Split by sentence-ending punctuation, keeping the delimiter
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for sentence in sentences:
            if len(sentence) > max_length:
                # Single sentence too long: split at word boundaries
                if current:
                    chunks.append(current)
                    current = ""
                words = sentence.split(' ')
                word_current = ""
                for word in words:
                    if len(word_current) + len(word) + 1 <= max_length:
                        word_current += (" " if word_current else "") + word
                    else:
                        if word_current:
                            chunks.append(word_current)
                        word_current = word
                current = word_current
            elif len(current) + len(sentence) + 1 <= max_length:
                current += (" " if current else "") + sentence
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text]


class DeepLTranslateService(TranslationService):
    """DeepL Translate API implementation.

    DeepL is the preferred engine for academic translation due to:
    - Superior sentence structure preservation
    - Better handling of long, complex academic sentences
    - Natural phrasing in translated text
    """

    DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
    DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Use pro endpoint if key doesn't end with ':fx'
        if api_key.endswith(':fx'):
            self.base_url = self.DEEPL_API_URL
        else:
            self.base_url = self.DEEPL_PRO_URL

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh"
    ) -> str:
        """Translate using DeepL API."""
        if not text.strip():
            return text

        protected_text, formulas = self.protect_formulas(text)

        # DeepL language code mapping
        lang_map = {
            "zh": "ZH", "en": "EN", "ja": "JA", "ko": "KO",
            "de": "DE", "fr": "FR", "es": "ES", "ru": "RU",
            "pt": "PT", "it": "IT", "nl": "NL"
        }
        target = lang_map.get(target_lang, target_lang.upper())
        source = lang_map.get(source_lang, source_lang.upper())

        try:
            # Split text into chunks (DeepL limit is ~50k chars per request)
            chunks = self._split_text(protected_text, max_length=30000)
            translated_parts = []

            async with httpx.AsyncClient(timeout=60.0) as client:
                for chunk in chunks:
                    response = await client.post(
                        self.base_url,
                        data={
                            "auth_key": self.api_key,
                            "text": chunk,
                            "source_lang": source,
                            "target_lang": target,
                            "preserve_formatting": "1",
                            "tag_handling": "xml",  # Protect XML-like tags
                        }
                    )
                    response.raise_for_status()
                    data = response.json()

                    for item in data.get("translations", []):
                        translated_parts.append(item["text"])

            translated = "".join(translated_parts)
            return self.restore_formulas(translated, formulas)

        except httpx.HTTPError as e:
            logger.error(f"DeepL HTTP error: {e}")
            raise Exception(f"DeepL API 请求失败: {e}")
        except Exception as e:
            logger.error(f"DeepL Translate error: {e}")
            raise

    def _split_text(self, text: str, max_length: int = 30000) -> List[str]:
        """Split text at sentence boundaries."""
        chunks = []
        current = ""

        sentences = re.split(r'(?<=[.!?])\s+', text)
        for sentence in sentences:
            if len(current) + len(sentence) + 1 <= max_length:
                current += (" " if current else "") + sentence
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks if chunks else [text]


class OpenAITranslateService(TranslationService):
    """OpenAI / DeepSeek translation via chat completion API.

    Uses a carefully crafted system prompt for academic translation quality,
    inspired by how tools like 小绿鲸 handle context-aware translation.
    """

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh"
    ) -> str:
        """Translate using OpenAI-compatible chat API."""
        if not text.strip():
            return text

        protected_text, formulas = self.protect_formulas(text)

        # Build terminology table for consistency
        # We'll extract key terms and provide them in the prompt
        term_map = {
            "zh": "Chinese (中文)",
            "en": "English",
            "ja": "Japanese",
            "ko": "Korean",
            "de": "German",
            "fr": "French",
        }

        system_prompt = f"""You are a professional academic translator specializing in scientific papers.
Translate the following text from {term_map.get(source_lang, source_lang)} to {term_map.get(target_lang, target_lang)}.

Rules:
1. Maintain academic writing style and formal tone
2. Keep technical terms accurate and consistent
3. Preserve all [[FORMULA_X]] placeholders exactly as they are - do not translate or modify them
4. Keep citations like [1], [2,3], (Smith et al., 2020) unchanged
5. Keep figure/table references like Fig.1, Table 2 unchanged
6. For abbreviations like CNN, LSTM, API, keep them in English
7. Ensure the translation reads naturally in the target language
8. Preserve paragraph structure
9. Do not add explanations or notes, only provide the translation"""

        # Split into chunks for long texts (GPT context limit)
        chunks = self._split_text(protected_text, max_length=4000)
        translated_parts = []

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for i, chunk in enumerate(chunks):
                    if i > 0:
                        await asyncio.sleep(0.3)  # Rate limiting

                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": chunk},
                            ],
                            "temperature": 0.1,  # Low temperature for consistency
                        }
                    )
                    response.raise_for_status()
                    data = response.json()

                    translated = data["choices"][0]["message"]["content"].strip()
                    translated_parts.append(translated)

            translated = "\n".join(translated_parts)
            return self.restore_formulas(translated, formulas)

        except httpx.HTTPError as e:
            logger.error(f"OpenAI HTTP error: {e}")
            raise Exception(f"OpenAI API 请求失败: {e}")
        except Exception as e:
            logger.error(f"OpenAI Translate error: {e}")
            raise

    def _split_text(self, text: str, max_length: int = 4000) -> List[str]:
        """Split text at paragraph boundaries."""
        paragraphs = text.split('\n')
        chunks = []
        current = ""

        for para in paragraphs:
            if not para.strip():
                if current:
                    chunks.append(current)
                    current = ""
                continue

            if len(current) + len(para) + 1 <= max_length:
                current += ("\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                # If single paragraph is too long, split at sentence boundary
                if len(para) > max_length:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    for sent in sentences:
                        if len(current) + len(sent) + 1 <= max_length:
                            current += (" " if current else "") + sent
                        else:
                            if current:
                                chunks.append(current)
                            current = sent
                else:
                    current = para

        if current:
            chunks.append(current)

        return chunks if chunks else [text]


class TranslationEngine:
    """Translation engine that manages different providers.

    Provider mapping:
    - google: Google Translate (free, via googletrans)
    - baidu: Baidu Translate (free, built-in API key)
    - deepl: DeepL Pro/Free API (requires API key)
    - openai: OpenAI GPT / DeepSeek (requires API key, best quality)
    """

    def __init__(self, provider: TranslationProvider, api_key: Optional[str] = None):
        self.provider = provider
        self.service = self._create_service(provider, api_key)

    def _create_service(
        self,
        provider: TranslationProvider,
        api_key: Optional[str]
    ) -> TranslationService:
        """Create translation service instance based on provider."""
        if provider == TranslationProvider.BAIDU:
            if not api_key:
                raise ValueError("百度翻译需要 API Key（格式: APP_ID|Secret_Key），请在设置中配置")
            parts = api_key.split("|", 1)
            if len(parts) != 2:
                raise ValueError("百度翻译 API Key 格式错误，应为 APP_ID|Secret_Key")
            return BaiduTranslateService(app_id=parts[0], secret_key=parts[1])
        elif provider == TranslationProvider.SUAPI:
            # Legacy: redirect to Google (free)
            return GoogleTranslateService()
        elif provider == TranslationProvider.DEEPL:
            if not api_key:
                raise ValueError("DeepL 翻译需要 API Key，请在设置中配置")
            return DeepLTranslateService(api_key)
        elif provider == TranslationProvider.OPENAI:
            if not api_key:
                raise ValueError("OpenAI 翻译需要 API Key，请在设置中配置")
            return OpenAITranslateService(api_key=api_key)
        elif provider == TranslationProvider.DEEPSEEK:
            if not api_key:
                raise ValueError("DeepSeek 翻译需要 API Key，请在设置中配置")
            return OpenAITranslateService(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1",
                model="deepseek-chat"
            )
        else:
            return GoogleTranslateService(api_key)

    async def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "zh"
    ) -> str:
        """Translate text using configured provider."""
        return await self.service.translate(text, source_lang, target_lang)

    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str = "en",
        target_lang: str = "zh"
    ) -> List[str]:
        """Translate multiple texts sequentially to respect rate limits.
        
        If a single chunk fails, the original text is kept in-place so that
        the overall translation can still complete.
        """
        results: List[str] = []
        failed_indices: List[int] = []

        for i, text in enumerate(texts):
            try:
                result = await self.translate(text, source_lang, target_lang)
                results.append(result)
            except Exception as e:
                logger.error(f"Translation failed for chunk {i}/{len(texts)}: {type(e).__name__}: {e!r}", exc_info=True)
                # Keep original text so the rest of the document can continue
                results.append(text)
                failed_indices.append(i + 1)
            # Small delay between requests
            await asyncio.sleep(0.3)

        if failed_indices:
            logger.warning(f"Batch finished: {len(failed_indices)}/{len(texts)} chunks failed (indices: {failed_indices})")
        return results
